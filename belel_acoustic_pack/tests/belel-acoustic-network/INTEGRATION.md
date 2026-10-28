# Parallel, non-destructive Belel testing

* This new package runs NO code when uploaded. Do not modify `src/App.tsx`, `src/main.tsx`, the orb, the voice context, or Belel's existing audio engine.
* Run `node --experimental-transform-types --test tests/belel-acoustic-network/*.test.ts` to execute isolated deterministic tests on Node.js 22.
* Review existing `src/lib/voice/AGENTS.md` before considering any future integration.
* The runtime never requests a microphone; all PCM frames must come from an already authorised Belel capture route.
* In an explicitly authorised development-only module, instantiate `new BelelAcousticNetwork()` and then `net.attachToExistingEvents(window)` to observe legacy events. This needs a future owner-approved import/entrypoint; simply uploading the files will not install the observer.
* Only after independent regression tests may a model be registered, owner-approved, licence-reviewed and enabled through `mode:'shadow',allowModelExecution:true,allowAudioToModel:true`. Never enable live output before voice identity and privacy tests.
* Wake recognition needs an actual separately trained wake-word model; this archive cannot fabricate validated weights.
* Moshi / PersonaPlex need externally deployed model servers and licensing approval; the optional codec translator is not a preinstalled GPU model.
