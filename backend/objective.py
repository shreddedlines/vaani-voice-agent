"""
determine_next_objective(state) -> Objective

This stands in for a future generic "Workflow Engine". It answers
"what should happen next?" based purely on which required slots are
still empty in `state` right now — recomputed fresh every turn.

Deliberately NOT a linear state graph (no `next:` pointers). A caller
who volunteers their timeline before being asked shouldn't confuse
this — we just look at what's still missing and pick the
highest-priority gap.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_config import AGENT_CONFIG
from state_store import CallState


@dataclass
class Objective:
    kind: str  # "collect_slot" | "wrap_up" | "end_call"
    slot: str | None
    instruction: str
    missing_slots: list[str]


def determine_next_objective(state: CallState) -> Objective:
    required = AGENT_CONFIG["required_slots"]
    descriptions = AGENT_CONFIG["slot_descriptions"]

    if state.is_terminal(AGENT_CONFIG["terminal_conditions"]):
        return Objective(
            kind="end_call",
            slot=None,
            instruction=(
                "The conversation has reached a natural conclusion.\n\n"
                "Before ending:\n"
                "- Briefly acknowledge the outcome of the conversation.\n"
                "- Mention any agreed next step if one exists.\n"
                "- Thank the caller for their time.\n"
                "- Wish them a good day.\n"
                "- End the conversation naturally.\n\n"
                "Do not end with only 'Goodbye'. "
                "Keep the closing warm, professional, and under three short sentences."
            ),
            missing_slots=[],
        )

    missing = state.missing_slots(required)

    if not missing:
        # All required slots filled but no terminal flag set yet —
        # nudge toward wrapping up (e.g. confirming the meeting decision).
        return Objective(
            kind="wrap_up",
            slot=None,
            instruction="All key information has been collected. Confirm next steps and close the call politely.",
            missing_slots=[],
        )

    next_slot = missing[0]
    return Objective(
        kind="collect_slot",
        slot=next_slot,
        instruction=descriptions.get(next_slot, f"Find out: {next_slot}"),
        missing_slots=missing,
    )
