"""
Unit tests for the parts of the system that don't need any API keys:
state store, objective function, and Conversation Manager business
rules. Run with:  python -m pytest backend/tests/ -v
(or just: python backend/tests/test_core_logic.py)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation_manager import ConversationManager
from objective import determine_next_objective
from state_store import CallState


class TestStateStore(unittest.TestCase):
    def test_slot_starts_empty(self):
        state = CallState()
        self.assertFalse(state.get_slot("project").is_filled())

    def test_slot_update_keeps_history(self):
        state = CallState()
        state.update_slot("timeline", "next month", confidence=0.8)
        state.update_slot("timeline", "next year", confidence=0.95)  # caller corrected themselves
        slot = state.get_slot("timeline")
        self.assertEqual(slot.value, "next year")
        self.assertEqual(len(slot.history), 1)
        self.assertEqual(slot.history[0].value, "next month")

    def test_missing_slots(self):
        state = CallState()
        state.update_slot("project", "modular kitchen")
        missing = state.missing_slots(["project", "timeline", "meeting_decision"])
        self.assertEqual(missing, ["timeline", "meeting_decision"])


class TestObjective(unittest.TestCase):
    def test_first_objective_is_first_missing_slot(self):
        state = CallState()
        obj = determine_next_objective(state)
        self.assertEqual(obj.kind, "collect_slot")
        self.assertEqual(obj.slot, "good_time_confirmed")

    def test_objective_skips_filled_slots_out_of_order(self):
        """Caller volunteers timeline before good_time_confirmed / project —
        objective should NOT insist on the rigid original order."""
        state = CallState()
        state.update_slot("timeline", "3 months")
        obj = determine_next_objective(state)
        self.assertEqual(obj.slot, "good_time_confirmed")  # still the first missing one, order-independent
        self.assertNotIn("timeline", obj.missing_slots)

    def test_wrap_up_when_all_slots_filled(self):
        state = CallState()
        for slot in ["good_time_confirmed", "project", "timeline", "meeting_decision"]:
            state.update_slot(slot, "yes")
        obj = determine_next_objective(state)
        self.assertEqual(obj.kind, "wrap_up")

    def test_terminal_when_meeting_booked(self):
        state = CallState()
        state.meeting_booked = True
        obj = determine_next_objective(state)
        self.assertEqual(obj.kind, "end_call")


class TestConversationManager(unittest.TestCase):
    def test_update_state_tool(self):
        cm = ConversationManager(phone_number="+919999999999")
        result = cm.apply_tool_call("update_state", {"slot": "project", "value": "modular kitchen", "confidence": 0.9})
        self.assertTrue(result["ok"])
        self.assertEqual(cm.get_state().get_slot("project").value, "modular kitchen")

    def test_book_meeting_rejected_without_project(self):
        """Business rule: Gemini can't finalize a meeting before the
        project is known, even if it calls the tool."""
        cm = ConversationManager(phone_number="+919999999999")
        result = cm.apply_tool_call("book_meeting", {"preferred_time": "Thursday 4pm"})
        self.assertFalse(result["ok"])
        self.assertFalse(cm.get_state().meeting_booked)

    def test_book_meeting_succeeds_with_project(self):
        cm = ConversationManager(phone_number="+919999999999")
        cm.apply_tool_call("update_state", {"slot": "project", "value": "modular kitchen", "confidence": 0.9})
        result = cm.apply_tool_call("book_meeting", {"preferred_time": "Thursday 4pm"})
        self.assertTrue(result["ok"])
        self.assertTrue(cm.get_state().meeting_booked)
        self.assertEqual(cm.get_state().meeting_time, "Thursday 4pm")

    def test_not_interested_sets_terminal_flag(self):
        cm = ConversationManager(phone_number="+919999999999")
        cm.apply_tool_call("mark_not_interested", {"reason": "just browsing"})
        self.assertTrue(cm.get_state().not_interested)
        obj = determine_next_objective(cm.get_state())
        self.assertEqual(obj.kind, "end_call")

    def test_unknown_tool_rejected(self):
        cm = ConversationManager(phone_number="+919999999999")
        result = cm.apply_tool_call("delete_database", {})
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
