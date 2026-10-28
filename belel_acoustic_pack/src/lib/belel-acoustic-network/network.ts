import { acousticSettings } from './config.ts';
import { BelelAcousticBus } from './bus.ts';
import { AcousticMetrics } from './metrics.ts';
import { BelelPronunciationCortex } from './pronunciation.ts';
import { BelelDuplexConductor } from './duplex.ts';
import { BelelModelRegistry } from './modelRegistry.ts';
import { observeExistingBelelEvents } from './legacyObserver.ts';
import type { AcousticSettings } from './types.ts';
/** New isolated network. Nothing runs until explicitly constructed and attached. */
export class BelelAcousticNetwork {
  readonly settings: AcousticSettings;
  readonly bus: BelelAcousticBus;
  readonly pronunciation: BelelPronunciationCortex;
  readonly duplex: BelelDuplexConductor;
  readonly registry: BelelModelRegistry;
  readonly metrics: AcousticMetrics;
  private detachFn: (() => void) | null = null;
  constructor(overrides: Partial<AcousticSettings> = {}) {
    this.settings = acousticSettings(overrides);
    this.bus = new BelelAcousticBus(this.settings.maximumEvents);
    this.pronunciation = new BelelPronunciationCortex();
    this.duplex = new BelelDuplexConductor(this.bus);
    this.registry = new BelelModelRegistry();
    this.metrics = new AcousticMetrics();
    if (this.settings.allowAggregateMetrics) {
      this.bus.subscribe('*', event => this.metrics.increment(event.type));
    }
  }
  attachToExistingEvents(target?: EventTarget): () => void {
    if (this.settings.mode === 'off') return () => {};
    if (this.detachFn) return this.detachFn;
    if (!target) { if (typeof window === 'undefined') return () => {}; target = window; }
    const stop = observeExistingBelelEvents(this.bus, target);
    this.detachFn = () => { stop(); this.detachFn = null; };
    return this.detachFn;
  }
  /** Explicit capability gate: no model, PCM, playback, or legacy listener takeover in default observe mode. */
  canUseModel(): boolean { return this.settings.allowModelExecution && (this.settings.mode === 'shadow' || this.settings.mode === 'active'); }
  canSendAudio(): boolean { return this.canUseModel() && this.settings.allowAudioToModel; }
  shutdown(): void { this.detachFn?.(); this.duplex.reset(); this.registry.listApproved().forEach(id=>this.registry.revoke(id)); this.bus.clear(); this.metrics.reset(); }
}
