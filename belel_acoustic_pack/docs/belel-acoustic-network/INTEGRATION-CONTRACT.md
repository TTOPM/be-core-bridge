# BAIN — Inbound integration contract, owner approval required

## Invariants

1. Existing Belel APIs, file contents and interface designs remain intact. No monkey-patching `SpeechRecognition`, AudioContext, TTS, `App.tsx`, `main.tsx` or network stores.
2. Never start a second microphone automatically. Future PCM adapters must receive data only from the owner-authorised current audio capture route.
3. There is one authoritative playback owner. BAIN observes voice playback, proposes pronunciation candidates and recommends yielding; it never directly injects speech into the production mixer.
4. The existing voice identity remains canonical. Full-duplex research model output defaults to evaluation-only, with no assistant-action permissions. External voice conditioning must be explicitly authorised.
5. No direct commands, payments, calls, memory writes, recordings or model downloads from network events.
6. All event subscribers are failure-isolated. If BAIN stops or crashes, legacy Belel continues unchanged.
7. Live model execution is disabled unless explicitly enabled AND all model-specific licence/sovereignty authorisations pass.
8. `Dessa` is a future compatibility target, **not** an included runtime or silent paid API call.

## Already observed events (read-only)

- `belel:tts:start` -> `tts.started`
- `belel:tts:end` -> `tts.ended`
- `belel:genesis:words` -> `speech.detected`
- `belel:genesis:recerror` -> `session.error`
- `belel:voice:duck` -> `duplex.yield`
- `belel:voice:restore` -> `duplex.resume`

No new global browser event listener is created merely by importing the module. A future owner-approved development entrypoint must instantiate the observer. Calling `shutdown()` detaches it.

## Example of a FUTURE authorised integration (not executed now)

```ts
import { BelelAcousticNetwork } from '@/lib/belel-acoustic-network';
const net = new BelelAcousticNetwork({ mode: 'observe' });
const detach = net.attachToExistingEvents(window);
// ... separately approved lifecycle integration
// detach(); net.shutdown();
```

### Proposed metadata contract for an existing capture adapter

`PCMFrame { pcm: Float32Array, sampleRate: 16000 | 24000, at: performance.now(), source:'existing-capture' }`.

Only the specific opt-in wake or duplex inference adapters may receive raw PCM; the event fabric strictly forbids raw audio. No cross-origin raw audio without secure deployment, authenticated access and explicit consent.

## Service integration details

- `LocalBelelWakeModel`: HTTP loopback service, 16k mono PCM, one float confidence response. The model is *not included*.
- `ExistingASRWakeVerifier`: independent confirmation of a candidate, not a blanket wake approval.
- `BelelSelfHostedDuplexGateway`: `belel.duplex.v1` JSON over WebSocket, 24k PCM16 audio frame; not the vendor-native Moshi protocol.
- `duplex_proxy.py`: separate opt-in translator from Belel JSON + PCM16 to **Moshi-family** 0x01/0x02 Opus protocol. Check the installed upstream version and endpoint; PersonaPlex has additional role, prompt and voice-conditioning requirements.

## Known constraints

- Browser/PWA cannot guarantee background always-on wake when suspended by the OS.
- A trained wake model requires collected licensed data and quality measurement. The package cannot deliver Siri/Alexa wake accuracy just by installation.
- Open speech-to-speech model output must not be mixed into Belel's signature voice without owner approval. Voice conditioning alone may not preserve Belel identity.
- External model server packages, Opus codecs and GPU/MLX hardware are optional and separately installed.
- If no existing mic-share API is available, a future minimal, reviewed adapter may be required. This package does NOT make such an edit.
