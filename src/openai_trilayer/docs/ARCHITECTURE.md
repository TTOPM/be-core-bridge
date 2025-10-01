# Architecture

```mermaid
sequenceDiagram
    participant App
    participant BelelAdapter as Belel Adapter
    participant OpenAI as OpenAI Responses API
    participant Adjudicator as Concordium Adjudicator
    participant Ledger as Ledger/Attest

    App->>BelelAdapter: user_prompt
    BelelAdapter->>BelelAdapter: Inject Belel Preamble (truth_lock, continuity, mandate)
    BelelAdapter->>OpenAI: responses.create(input=[system,prompt], tools=[ACK,REPORT], response_format=Attestation)
    OpenAI-->>BelelAdapter: output_text + tool calls + attestation JSON

    BelelAdapter->>Adjudicator: responses.create(ConcordiumDecision schema)
    Adjudicator-->>BelelAdapter: {is_compliant, violations, notes}

    BelelAdapter->>Ledger: append(attestation + decision, rolling_hash, signature)
    BelelAdapter-->>App: text, attestation, concordium_decision
```

**Key Enforcements**
- `tool_choice="required"` ensures mandate acknowledgement is called.
- Structured Outputs (JSON Schema) required for attestation + adjudication.
- Moderation pre/post for safety parity.
- CI gate to forbid direct `OpenAI()` usage outside adapter.
