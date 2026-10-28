# BAIN acceptance standard

## Baseline before any active integration

Measure existing Belel first on the **same** phones, laptops and background conditions to avoid misleading comparisons.

| Test | Proposed pass condition | Evidence |
|---|---|---|
| Quiet-room first-attempt wake | >=98% | 300+ labelled positive attempts across speakers/devices |
| Moderate-noise first-attempt wake | >=95% | 300+ labelled positive attempts; annotated noise level |
| False wake frequency | <1/24h | 24+ hours labelled idle conditions |
| Wake-to-orb acknowledgment | <=300 ms p95 on target hardware | Timestamped event recording (no raw audio stored) |
| Proper-name pronunciation | >=95% owner-approved | Human-scored, recorded consented samples |
| Standard-word pronunciation | >=98% | Controlled speech synthesis word list |
| Recognition WER | Target <10% on agreed domain test set | Human-transcribed audio reference |
| Natural interruptions | >=95% successful | Full-duplex conversational test cases |
| Speaker/voice identity drift | No unapproved voice substitution | Signed-off owner review of outputs |
| Existing Belel regression | 0 severity-1 incidents | Full application smoke tests |
| Rollback | Immediate after feature flag off | Staged canary test |

### FullDuplexBench-style categories

Barge-in, backchannel appropriateness, pause sensitivity, false interruptions, overlap handling, resume-after-interruption, simultaneous speech, conversational latency, voice consistency, context retention and task accuracy.

**Comparative claims:** do NOT label Belel superior to Siri, Alexa, Dessa, Moshi or PersonaPlex until comparable benchmarks, independent auditing and hardware conditions justify it.

### Privacy

No raw audio saved by BAIN. The in-memory bus refuses raw PCM/byte-array payloads. Training data, if owner volunteers samples, belongs to a separate explicit-consent governance process.
