import { BelelAcousticBus } from './bus.ts';
/** Read-only adapter to Belel's established event names; NEVER dispatches an event to an existing subsystem. */
export function observeExistingBelelEvents(bus: BelelAcousticBus, target: EventTarget): () => void {
  const bindings: Array<[string, () => void]> = [];
  const listen = (legacy: string, type: Parameters<BelelAcousticBus['publish']>[0], payload: Record<string, unknown>) => {
    const fn: EventListener = () => { bus.publish(type, 'belel.legacy-observer', payload); };
    target.addEventListener(legacy, fn);
    bindings.push([legacy, () => target.removeEventListener(legacy, fn)]);
  };
  listen('belel:tts:start', 'tts.started', { legacy: true });
  listen('belel:tts:end', 'tts.ended', { legacy: true });
  listen('belel:genesis:words', 'speech.detected', { legacy: true });
  listen('belel:genesis:recerror', 'session.error', { legacy: true });
  listen('belel:voice:duck', 'duplex.yield', { legacy: true });
  listen('belel:voice:restore', 'duplex.resume', { legacy: true });
  return () => { for (const [, unsubscribe] of bindings) unsubscribe(); };
}
