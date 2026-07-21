"""
ConversationManager

Owns exactly four responsibilities (per architecture discussion):
  1. Maintain conversation state (delegates to CallState)
  2. Validate tool calls Gemini proposes
  3. Update slots
  4. Track conversation progress (terminal flags)

It does NOT know it's talking about kitchens, Sunrise Interiors, or
interior design — that knowledge lives in agent_config.py and
prompts.py. This class would be reused unchanged for a dentist or
insurance agent.

Gemini proposes actions via tool calls; this class decides what
actually happens. That separation is intentional — a misheard word
should never be able to single-handedly "confirm" a meeting; it has
to pass through here first.
"""

from __future__ import annotations

from typing import Any
import re

from state_store import CallState
from objective import determine_next_objective, Objective

def is_valid_time_expression(value: str) -> bool:
    """
    Very loose heuristic to ensure the LLM isn't passing a conversational filler
    like 'not specified yet' or 'unknown' into the meeting_time slot.
    Accepts values that contain legitimate time-related words or numbers.
    """
    val = value.lower()
    time_markers = ["am", "pm", "morning", "afternoon", "evening", "today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    # If it contains digits (like "10:30" or "4"), it's likely a time
    if any(char.isdigit() for char in val):
        return True
        
    # If it contains common time words
    if any(marker in val for marker in time_markers):
        return True
        
    return False


def is_valid_project_expression(value: str) -> bool:
    """
    Heuristic to reject hallucinated or invalid project types 
    (e.g., 'Everything', or dimensions like '3 kilometers').
    """
    val = value.lower()
    invalid_exacts = {"everything", "all", "nothing", "unsure", "unknown", "not sure"}
    if val.strip() in invalid_exacts:
        return False
        
    # Reject physical dimensions that indicate size, not project type
    size_markers = {"kilometer", "km", "meter", "sqft", "square feet", "mile"}
    if any(char.isdigit() for char in val) and any(marker in val for marker in size_markers):
        return False
        
    return True


class ConversationManager:
    def __init__(self, phone_number: str):
        self.state = CallState(phone_number=phone_number)

    # ---- tool call entry point -------------------------------------------------

    def apply_tool_call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Validate + apply a tool call Gemini proposed. Returns a small result
        dict that gets fed back to the LLM as the tool result."""
        handler = getattr(self, f"_handle_{name}", None)
        if handler is None:
            return {"ok": False, "error": f"unknown tool '{name}'"}
        return handler(args)

    # ---- individual tool handlers -----------------------------------------------

    def _handle_update_state(self, args: dict[str, Any]) -> dict[str, Any]:
        slot = args.get("slot")
        value = args.get("value")
        if isinstance(value, str) and value.strip().lower() in {
            "unknown",
            "unsure",
            "none",
            "null",
            "",
        }:
            return {
                "ok": False,
                "error": "Only record information explicitly provided by the caller."
            }
            
        if slot == "meeting_time" and isinstance(value, str):
            if not is_valid_time_expression(value):
                return {
                    "ok": False,
                    "error": f"'{value}' does not look like a legitimate day/time expression. Ask the user for the actual time."
                }
                
        if slot == "project" and isinstance(value, str):
            if not is_valid_project_expression(value):
                return {
                    "ok": False,
                    "error": f"'{value}' is ambiguous or invalid for a project type. Ask the user for clarification instead of guessing."
                }
            
        existing = self.state.get_slot(slot)
        if existing.is_filled():
            # Idempotent: ignore updates to slots that are already filled.
            return {"ok": True, "redundant": True, "slot": slot, "value": value}
            
        self.state.update_slot(slot, value)
        
        # Determine terminal transitions automatically
        self.evaluate_state()
        
        return {"ok": True, "slot": slot, "value": value}

    def evaluate_state(self):
        """Evaluate if the current state transitions the call to a terminal state."""
        decision = self.state.get_slot("meeting_decision").value
        time_slot = self.state.get_slot("meeting_time").value
        project_slot = self.state.get_slot("project")

        # 1. Successful meeting booked
        if decision == "yes" and time_slot and project_slot.is_filled():
            if not self.state.meeting_booked:
                self.state.meeting_booked = True
                self.state.call_ended = True
                
        # 2. Caller not interested
        elif decision == "no":
            if not self.state.not_interested:
                self.state.not_interested = True
                self.state.call_ended = True

    def get_state(self) -> CallState:
        return self.state
        
    def get_next_objective(self) -> Objective:
        return determine_next_objective(self.state)
