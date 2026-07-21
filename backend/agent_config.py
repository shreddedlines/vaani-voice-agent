"""
Agent configuration for the Sunrise Interiors call-back agent.

Per the architecture discussion: we are NOT building a generic,
config-driven workflow engine yet (that's premature with only one
business). Instead this is a single plain dict, isolated in its own
file, that objective.py and prompts.py read from. If a second business
shows up later, this is exactly the shape that would get extracted
into YAML / a database row per agent.
"""

AGENT_CONFIG = {
    "persona_name": "Aisha",
    "company_name": "Sunrise Interiors",
    "tts_aggregation_mode": "sentence",  # options: "sentence", "phrase", "token"

    # Slots we want filled before the call is "done", in priority order.
    # objective.py picks the first missing one each turn — this is NOT
    # a rigid sequence, callers can fill these in any order.
    "required_slots": [
        "good_time_confirmed",
        "project",
        "timeline",
        "meeting_decision",
        "meeting_time",
    ],

    # Any one of these being true ends the call.
    "terminal_conditions": [
        "meeting_booked",
        "not_interested",
        "call_ended",
    ],

    # Human-readable description of each slot, used when building the
    # "collect this next" instruction for the LLM.
    "slot_descriptions": {
        "good_time_confirmed": "Confirm it's a good time for the caller to talk right now.",
        "project": "What renovation/interior work they want done (e.g. modular kitchen, full flat interior).",
        "timeline": "How soon they want to start the work.",
        "meeting_decision": "Whether the caller wants to schedule a meeting with a designer (yes/no).",
        "meeting_time": "Ask for the caller's preferred meeting day and time. Do not use the renovation timeline as the meeting time.",
    },
}
