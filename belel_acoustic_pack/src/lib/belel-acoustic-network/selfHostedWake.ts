import type { PCMFrame } from './types.ts';
import type { BelelWakeDetector } from './wake.ts';
function pcm16Base64(pcm: Float32Array): string {
  const out = new Uint8Array(pcm.length * 2); const v = new DataView(out.buffer);
  for (let i = 0; i < pcm.length; i++) v.setInt16(i * 2, Math.max(-32768, Math.min(32767, Math.round(Math.max(-1, Math.min(1, pcm[i])) * 32767))), true);
  let str = ''; for (let i = 0; i < out.length; i += 0x4000) str += String.fromCharCode(...out.subarray(i, i + 0x4000));
  return btoa(str);
}
/** Actual model adapter to the optional self-hosted openWakeWord inference server.
 * No trained model is bundled, so the owner controls its provenance and commercial licence.
 * This adapter must receive PCM from an EXISTING authorised capture path.
 */
export class LocalBelelWakeModel implements BelelWakeDetector {
  readonly id = 'belel-custom-openwakeword';
  constructor(private readonly endpoint = 'http://127.0.0.1:8791', private readonly fetcher: typeof fetch = fetch) {
    const url = new URL(endpoint);
    if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) throw new Error('Only local wake inference endpoints are allowed');
  }
  async score(frame: PCMFrame): Promise<number> {
    if (frame.sampleRate !== 16000) throw new Error('Wake model expects 16 kHz mono PCM');
    if (!frame.pcm.length || frame.pcm.length > 32_000) throw new Error('Expected 0–2 seconds of existing audio');
    const ctrl = new AbortController(); const timer = setTimeout(() => ctrl.abort(), 1800);
    try {
      const res = await this.fetcher(`${this.endpoint}/v1/wake`, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ pcm16le_b64: pcm16Base64(frame.pcm), sample_rate: 16000 }), signal: ctrl.signal,
      });
      if (!res.ok) throw new Error(`Wake gateway HTTP ${res.status}`);
      const body: { confidence?: number } = await res.json();
      if (!Number.isFinite(body.confidence) || body.confidence! < 0 || body.confidence! > 1) throw new Error('Malformed wake score');
      return body.confidence!;
    } finally { clearTimeout(timer); }
  }
}
/** This second-stage verifier is text-based and optional; fail closed on errors.
 * A separate, independent model should verify acoustic positives in production.
 */
export class ExistingASRWakeVerifier {
  constructor(private readonly transcribe: (frame: PCMFrame) => Promise<string>, private readonly expected = /\b(?:hey\s+)?(?:belel|bel\s*el|bilal)\b/i) {}
  async verify(frame: PCMFrame): Promise<number> {
    const text = (await this.transcribe(frame)).slice(0, 300);
    return this.expected.test(text) ? 0.95 : 0;
  }
}
