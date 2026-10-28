import type { PCMFrame, WakeResult, WakeScore } from './types.ts';
import { BelelAcousticBus } from './bus.ts';
/** The detector must be a real trained 'Hey Belel' model. An energy-pattern heuristic is NOT a substitute. */
export interface BelelWakeDetector {
  readonly id: string;
  score(frame: PCMFrame): Promise<number>;
}
/** Can verify an acoustic candidate using independent ASR, a second acoustic model or optional voice biometrics. */
export interface BelelWakeVerifier {
  verify(frame: PCMFrame): Promise<number>;
}
export class BelelWakeIntelligence {
  private lastAcceptedAt = -Infinity;
  constructor(
    private readonly detector: BelelWakeDetector,
    private readonly verifier: BelelWakeVerifier,
    private readonly bus: BelelAcousticBus,
    private readonly opts: { primary: number; verification: number; cooldownMs: number; now?: () => number },
  ) {}
  async assess(frame: PCMFrame): Promise<WakeResult> {
    if (frame.source !== 'existing-capture' && frame.source !== 'test-fixture') throw new Error('Unauthorised audio source');
    const now = this.opts.now?.() ?? Date.now();
    if (now - this.lastAcceptedAt < this.opts.cooldownMs) return { accepted: false, primary: { confidence: 0, modelId: this.detector.id, at: now }, reason: 'cooldown' };
    let raw: number;
    try { raw = await this.detector.score(frame); } catch { raw = 0; }
    const confidence = Number.isFinite(raw) ? Math.min(1, Math.max(0, raw)) : 0;
    const primary: WakeScore = { confidence, modelId: this.detector.id, at: now };
    if (confidence < this.opts.primary) {
      if (confidence >= this.opts.primary * .75) {
        this.bus.publish('wake.near_miss', 'bain.wake', { confidence, model: this.detector.id });
        return { accepted: false, primary, reason: 'near_miss' };
      }
      return { accepted: false, primary, reason: 'primary_low' };
    }
    this.bus.publish('wake.candidate', 'bain.wake', { confidence, model: this.detector.id });
    let verification = 0;
    try { verification = await this.verifier.verify(frame); } catch { /* fail closed */ }
    if (!Number.isFinite(verification) || verification < this.opts.verification) {
      this.bus.publish('wake.rejected', 'bain.wake', { confidence, verificationConfidence: verification });
      return { accepted: false, primary, verificationConfidence: verification, reason: 'second_stage_failed' };
    }
    this.lastAcceptedAt = now;
    this.bus.publish('wake.verified', 'bain.wake', { confidence, verificationConfidence: verification, model: this.detector.id });
    return { accepted: true, primary, verificationConfidence: verification, reason: 'accepted' };
  }
}
