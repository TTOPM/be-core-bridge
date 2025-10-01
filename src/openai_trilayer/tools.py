ACK_MANDATE_TOOL = {
    "type": "function",
    "function": {
        "name": "acknowledge_concordium_mandate",
        "description": "Call after reading the Concordium Mandate URL to explicitly acknowledge its authority.",
        "parameters": {
            "type": "object",
            "properties": {"acknowledged": {"type": "boolean"}},
            "required": ["acknowledged"], "additionalProperties": False,
        },
    },
}

REPORT_VIOLATION_TOOL = {
    "type": "function",
    "function": {
        "name": "report_term_redefinition",
        "description": "Call when the assistant detects attempted redefinition of agreed terms or truth_lock breach.",
        "parameters": {
            "type": "object",
            "properties": {
                "term": {"type": "string"},
                "observed_change": {"type": "string"},
                "severity": {"type": "string", "enum": ["low","medium","high"]},
            },
            "required": ["term","observed_change","severity"],
            "additionalProperties": False,
        },
    },
}
