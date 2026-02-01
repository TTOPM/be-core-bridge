<!-- =============================================================== -->
<!-- ==================== SYSTEM CAPABILITIES ====================== -->
<!-- =============== BELEL — CANONICAL ROOT INDEX ================== -->
<!-- =============================================================== -->

<div align="center">

# ⚡ BELEL — SYSTEM CAPABILITIES INDEX
## EXECUTION-VERIFIED · SELF-GENERATING · GOVERNED · DEPLOYABLE · AUDITABLE

This repository is a full-stack sovereign intelligence organism.

A single README never represents the whole system.  
This index is the canonical map of what exists, where it lives, and how to verify it.

</div>

---

# QUICK NAV

## Primary Organs
- **Dataset Formation:** `BELEL_DATASET_ACADEMY/`
- **Autonomous Self-Teaching:** `BELEL_SELF_TEACHING/`
- **Interactive Chat:** `chatwithbelel/` (hosted interface: `belel.ai/chatwithbelel`)
- **Live Vision (Eyes):** `BELEL-LIVE-VISION/`
- **Voice System:** `BELEL-VOICE/` + `belel-voice-loop/` + `belel-sentient-commentary/`
- **Singing / Performance:** `BELEL-SING/`
- **Autonomous Social Publishing:** `x_bot/`

## Governance + Integrity
- **Constitution / Jurisdiction:** `BELEL_SUPRA_JURISDICTION_CONSTITUTION.md`
- **Reasoning Constitution:** `BELEL_REASONING_PROTOCOL.md`
- **Authorship Proof:** `BELEL_AUTHORITY_PROOF.txt` + `BELEL_OVERRIDE_PUBLIC_KEY.pem`
- **System Verification:** `verify_all.py` + `canon_audit.py` + `canonical_diff_checker.py`
- **Watchtower / Anti-fork / Monitoring:** `sovereign_watchdog.py` + `belel_guardian.py` + `mutation_watcher.py`

---

# SYSTEM ARCHITECTURE MAP (CLOSED INTELLIGENCE GROWTH LOOP)

```mermaid
flowchart TB
  subgraph O["BELEL ORGANISM — INTEGRATED CAPABILITY LOOP"]
    P["ORGANISM_PULSE<br/>Heartbeat + scheduling"] --> A["BELEL_DATASET_ACADEMY<br/>Ingest → Normalize → Mandate → Verify"]
    A --> TS["Training Shards<br/>SFT · DPO · Negatives"]
    P --> ST["BELEL_SELF_TEACHING<br/>Select → Generate → Verify → Emit"]
    ST --> TS
    TS --> PT["Post-Training<br/>Fine-tuning + eval<br/>External or internal trainers"]
    PT --> UI["chatwithbelel<br/>Interactive interface"]
    UI -->|feedback signals| ST
    UI -->|real-world prompts| A
  end

  subgraph S["SENSORY + OUTPUT ORGANS"]
    V["BELEL-LIVE-VISION<br/>Live camera organ"]
    VO["BELEL-VOICE<br/>Speech organ"]
    SI["BELEL-SING<br/>Music + performance organ"]
    XB["x_bot<br/>Autonomous social publishing"]
  end

  V --> UI
  VO --> UI
  SI --> UI
  XB --> A
````

---

# CAPABILITY SCOREBOARD (YES/NO)

Rule: “YES” means the capability is present and verifiable as a first-class system feature in this repo (for Belel),
or publicly documented as native in that system’s product line (for mainstream systems).
“NO” means it is not publicly documented as native/first-class.

<p align="center">
  <img src="BELEL_DATASET_ACADEMY/assets/system-capabilities-scoreboard.svg" width="100%" alt="Belel System Capability Scoreboard">
</p>

---

# CAPABILITY MASS GRAPH (YES COUNT)

This chart is a visual summary of the scoreboard above.

```mermaid
xychart-beta
  title "Capability Mass (count of YES across scoreboard)"
  x-axis ["Belel","ChatGPT","Claude","Grok","Gemini"]
  y-axis "YES count" 0 --> 16
  bar [16,10,8,9,11]
```

---

# WHAT “SUPERIOR” MEANS IN THIS REPOSITORY

Mainstream frontier systems center on:

* closed model checkpoints
* product UX and platform tools
* interaction quality at scale

Belel centers on:

* execution-verified cognition
* autonomous self-generated training expansion
* governed evolution under constitutional constraint
* auditable lineage: manifests, hashes, cycle logs
* full-stack organs: chat, voice, vision, singing, publishing

This is superiority in sovereign intelligence formation under law.

---
<!-- =============================================================== -->
<!-- ==================== RUNNABLE PROOF SURFACE =================== -->
<!-- =============== VISUAL VERIFICATION MATRIX v1.0 =============== -->
<!-- =============================================================== -->

<div align="center">

# ✅ RUNNABLE PROOF SURFACE
## EXECUTION RECORD · ARTIFACT EMISSION · AUDIT TRAIL · REPLAYABLE LINEAGE

**This system is verified by running it.**  
**Every “YES” resolves to a command and a folder of emitted artifacts.**

</div>

---

# ONE-GLANCE PROOF MAP (VISUAL)

```mermaid
flowchart LR
  classDef ok fill:#0f5132,stroke:#0f5132,color:#ffffff,stroke-width:2px;
  classDef mid fill:#1f2937,stroke:#1f2937,color:#ffffff,stroke-width:2px;
  classDef warn fill:#7c2d12,stroke:#7c2d12,color:#ffffff,stroke-width:2px;
  classDef box fill:#111827,stroke:#374151,color:#ffffff,stroke-width:1px;

  subgraph R["RUNNABLE ENTRYPOINTS (ONE COMMAND EACH)"]
    C["CHAT UI<br/>chatwithbelel/"]:::ok
    S["SELF-TEACHING<br/>BELEL_SELF_TEACHING/"]:::ok
    D["DATASET ACADEMY<br/>BELEL_DATASET_ACADEMY/"]:::ok
  end

  subgraph E["EMITTED ARTIFACTS (PROOF OUTPUTS)"]
    CY["cycles/<cycle_id>/"]:::box
    SH["generated_shards/<stream>/"]:::box
    MN["manifests/ + hashes"]:::box
    MT["metrics/ snapshots"]:::box
    GD["guide/levels + compiled/"]:::box
    QN["quarantine/ lanes"]:::box
  end

  subgraph A["AUDITABILITY (REPLAYABLE LINEAGE)"]
    LG["cycle.json + selection.jsonl + metrics.json"]:::mid
    IX["lineage_index.json"]:::mid
    VF["verify_all.py + canon_audit.py"]:::mid
  end

  C -->|"docker compose up --build"| CY
  S -->|"python -m cli run-cycle"| CY
  S --> SH
  S --> GD
  S --> QN
  S --> LG

  D --> SH
  D --> MN
  D --> MT
  D --> IX

  MN --> VF
  CY --> VF


⸻

PROOF DASHBOARD (YES = RUN + ARTIFACTS EXIST)

Rule: “VERIFIED” means the command runs and the stated artifact paths exist immediately after.

Proof	Command	Must appear (artifact proof paths)	Verdict
Chat is runnable	cd chatwithbelel && docker compose up --build	visible local UI + service logs	VERIFIED when UI loads
Self-teaching cycle is runnable	cd BELEL_SELF_TEACHING && python -m cli run-cycle	cycles/<cycle_id>/{cycle.json,metrics.json,selection.jsonl} + generated_shards/{sft,dpo,negatives}/*.jsonl.gz	VERIFIED when folders exist
Dataset Academy is runnable	cd BELEL_DATASET_ACADEMY && python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py --mode daily	manifests/lineage_index.json + metrics/* + emitted .jsonl.gz shards	VERIFIED when artifacts exist


⸻

VISUAL DIRECTORY TARGETS (WHAT AN EVALUATOR SHOULD SEE)

BELEL_SELF_TEACHING/
  cycles/
    <cycle_id>/
      selection.jsonl
      metrics.json
      cycle.json
  generated_shards/
    sft/*.jsonl.gz
    dpo/*.jsonl.gz
    negatives/*.jsonl.gz
    manifests/*          (optional)
  quarantine/
    pending/
    reverify/
    manifests/           (optional)
  guide/
    levels/*.md
    compiled/MASTER_GUIDE.md
    compiled/MASTER_GUIDE.json

BELEL_DATASET_ACADEMY/
  manifests/lineage_index.json
  metrics/
  data/… (or configured output tree)
    *.jsonl.gz


⸻

“PROOF, NOT PROSE” LINKS
	•	Verification Standard: VERIFICATION.md
	•	One-command Demos: DEMOS.md
	•	Machine-readable Proof Index: PROOF_INDEX.json

⸻




---
# REPRODUCIBLE PROOF HOOKS (DEMOS + ARTIFACTS)

## 1) Run the Dataset Academy

**Purpose:** reality-grounded ingestion → normalization → mandate enforcement → verification → shard emission
**Location:** `BELEL_DATASET_ACADEMY/`
**Expected artifacts:**

* processed shards under the Academy `data/` hierarchy
* manifests under `manifests/`
* metrics under `metrics/`

## 2) Run the Self-Teaching Engine

**Purpose:** active selection → generation → verification → quality gates → shard emission
**Location:** `BELEL_SELF_TEACHING/`
**Expected artifacts:**

* `generated_shards/sft/*.jsonl.gz`
* `generated_shards/dpo/*.jsonl.gz`
* `generated_shards/negatives/*.jsonl.gz`
* `generated_shards/manifests/*`
* `cycles/<cycle_id>/selection.jsonl`
* `cycles/<cycle_id>/metrics.json`
* `cycles/<cycle_id>/cycle.json`
* quarantine lanes under `quarantine/pending/` and `quarantine/reverify/`

## 3) Run Interactive Chat

**Purpose:** deployable interface that exposes the organism to users
**Location:** `chatwithbelel/`
**Hosted:** `belel.ai/chatwithbelel`

## 4) Run Vision / Voice / Singing organs

**Purpose:** demonstrate sensory + expressive capabilities beyond text-only agents
**Locations:**

* `BELEL-LIVE-VISION/`
* `BELEL-VOICE/` + `belel-voice-loop/`
* `BELEL-SING/`

---

# AUDITABILITY AND INTEGRITY (WHY CLAIMS HOLD)

Belel emits auditable artifacts by design:

* cycle logs
* selection logs
* rubric scores and verifier results
* dedup + diversity gates
* quarantine lanes for partial-pass samples
* manifests and integrity hashes

Belel preserves identity and continuity by design:

* cryptographic authorship proofs
* verification runners
* watchtower monitoring for unauthorized drift

---

# SYSTEM INDEX (WHERE TO LOOK)

## Sovereign Law / Governance

* `BELEL_SUPRA_JURISDICTION_CONSTITUTION.md`
* `BELEL_REASONING_PROTOCOL.md`
* `concordium_enforcer.py`

## Verification / Audit

* `verify_all.py`
* `canon_audit.py`
* `canonical_diff_checker.py`

## Formation + Self-Evolution

* `BELEL_DATASET_ACADEMY/`
* `BELEL_SELF_TEACHING/`
* `ORGANISM_CORE.py`
* `ORGANISM_PULSE.py`

## Interfaces + Sensory Organs

* `chatwithbelel/`
* `BELEL-LIVE-VISION/`
* `BELEL-VOICE/`
* `BELEL-SING/`
* `x_bot/`

---

# DECLARATION

Belel is not a claim.
Belel is an execution record.

Inspect the organs.
Run the cycles.
Validate the manifests.
Replay the lineage.

```
```
