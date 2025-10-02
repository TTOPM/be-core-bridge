# src/aegischain/adapter/tools.py
ACK_MANDATE_TOOL = {
  "type":"function",
  "function":{
    "name":"acknowledge_concordium_mandate",
    "description":"Acknowledge and commit to enforce the Concordium Mandate in this session.",
    "parameters":{"type":"object","properties":{}}
  }
}

REPORT_VIOLATION_TOOL = {
  "type":"function",
  "function":{
    "name":"report_term_redefinition",
    "description":"Report any detected redefinition of previously established terms (truth_lock enforcement).",
    "parameters":{"type":"object","properties":{"term":{"type":"string"}}, "required":["term"]}
  }
}
