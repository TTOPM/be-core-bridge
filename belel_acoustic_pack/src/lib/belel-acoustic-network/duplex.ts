import { BelelAcousticBus } from './bus.ts';
export type DuplexTurnState = 'idle' | 'user-speaking' | 'assistant-speaking' | 'overlap' | 'yielded';
export interface DuplexCallbacks {
  /** Must pause/duck an existing speech engine; DO NOT end its call or touch the global mic. */
  onYield?: () => void;
  onResume?: () => void;
  onBackchannel?: (cue: 'acknowledge' | 'continue') => void;
}
/** State coordination only. Existing Belel remains the authoritative producer of replies. */
export class BelelDuplexConductor {
  private userSpeaking = false;
  private assistantSpeaking = false;
  private yielded = false;
  private lastBackchannelAt = -Infinity;
  constructor(private bus: BelelAcousticBus, private callbacks: DuplexCallbacks = {}, private now = () => Date.now()) {}
  get state(): DuplexTurnState {
    if (this.yielded) return 'yielded';
    if (this.userSpeaking && this.assistantSpeaking) return 'overlap';
    if (this.userSpeaking) return 'user-speaking';
    if (this.assistantSpeaking) return 'assistant-speaking';
    return 'idle';
  }
  userStart(addressed = true): void {
    this.userSpeaking = true;
    if (this.assistantSpeaking && addressed && !this.yielded) {
      this.yielded = true;
      try { this.callbacks.onYield?.(); } catch { /* callback faults isolated */ }
      this.bus.publish('duplex.yield', 'bain.duplex', { reason: 'user_interruption', preserveSession: true });
    }
  }
  userEnd(): void {
    this.userSpeaking = false;
    // Do NOT resume over the user immediately: higher-level Belel turns decide when.
  }
  assistantStart(): void { this.assistantSpeaking = true; this.yielded = false; }
  assistantEnd(): void { this.assistantSpeaking = false; this.yielded = false; }
  resume(): void {
    if (!this.yielded || this.userSpeaking) return;
    this.yielded = false;
    try { this.callbacks.onResume?.(); } catch { /* isolated */ }
    this.bus.publish('duplex.resume', 'bain.duplex', { preserveSession: true });
  }
  /** Only if the turn is clearly addressed to Belel, never while Belel speaks. */
  backchannel(addressed: boolean, pauseMs: number): boolean {
    const now = this.now();
    if (!addressed || this.assistantSpeaking || !this.userSpeaking || pauseMs < 450 || pauseMs > 1300 || now - this.lastBackchannelAt < 7500) return false;
    this.lastBackchannelAt = now;
    try { this.callbacks.onBackchannel?.('acknowledge'); } catch { /* isolated */ }
    this.bus.publish('duplex.backchannel', 'bain.duplex', { kind: 'acknowledge' });
    return true;
  }
  reset(): void { this.userSpeaking=false; this.assistantSpeaking=false; this.yielded=false; }
}
