import type { AcousticEvent, AcousticEventName } from './types.ts';
type Listener = (event: AcousticEvent) => void;
/** In-process event fabric: no network traffic, disk writes, raw audio, or automatic legacy commands. */
export class BelelAcousticBus {
  private listeners = new Map<AcousticEventName | '*', Set<Listener>>();
  private seq = 0;
  private events: AcousticEvent[] = [];
  constructor(private readonly maxEvents = 200, private readonly clock = () => Date.now()) {
    if (!Number.isInteger(maxEvents) || maxEvents < 1 || maxEvents > 1000) throw new Error('Invalid bus capacity');
  }
  subscribe(type: AcousticEventName | '*', listener: Listener): () => void {
    let set = this.listeners.get(type);
    if (!set) { set = new Set(); this.listeners.set(type, set); }
    set.add(listener);
    return () => { set?.delete(listener); if (!set?.size) this.listeners.delete(type); };
  }
  publish<T extends Record<string, unknown>>(type: AcousticEventName, source: string, payload: T, correlationId?: string): AcousticEvent<T> {
    if (!/^[a-z0-9.:-]{2,100}$/i.test(source)) throw new Error('Invalid acoustic source');
    // Raw audio cannot be published to the telemetry fabric.
    for (const [key, value] of Object.entries(payload)) {
      if (value instanceof Float32Array || value instanceof Uint8Array || value instanceof ArrayBuffer || /^(audio|rawAudio|pcm|waveform)$/i.test(key)) throw new Error('Raw audio forbidden on acoustic bus');
    }
    const event: AcousticEvent<T> = Object.freeze({ schema: 'belel.acoustic.v1', id: `bain-${this.clock()}-${++this.seq}`, type, source, at: this.clock(), correlationId, payload: Object.freeze({ ...payload }) });
    this.events.push(event as AcousticEvent);
    if (this.events.length > this.maxEvents) this.events.splice(0, this.events.length - this.maxEvents);
    for (const fn of [...(this.listeners.get(type) ?? []), ...(this.listeners.get('*') ?? [])]) {
      try { fn(event as AcousticEvent); } catch { /* observer failures cannot affect Belel */ }
    }
    return event;
  }
  recent(limit = 30): AcousticEvent[] { return this.events.slice(-Math.max(0, Math.min(limit, this.maxEvents))); }
  clear(): void { this.events = []; }
}
