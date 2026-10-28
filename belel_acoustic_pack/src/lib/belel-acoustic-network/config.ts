import type { AcousticSettings } from './types.ts';
export const BELEL_ACOUSTIC_DEFAULTS: Readonly<AcousticSettings> = Object.freeze({
  mode: 'observe', allowModelExecution: false, allowAudioToModel: false,
  allowAggregateMetrics: false, wakePrimaryThreshold: 0.84,
  wakeVerificationThreshold: 0.72, wakeCooldownMs: 2_000, maximumEvents: 200,
});
export function acousticSettings(overrides: Partial<AcousticSettings> = {}): AcousticSettings {
  const s = { ...BELEL_ACOUSTIC_DEFAULTS, ...overrides };
  if (!Number.isFinite(s.wakePrimaryThreshold) || s.wakePrimaryThreshold < 0.5 || s.wakePrimaryThreshold > 0.999) throw new Error('Invalid primary wake threshold');
  if (!Number.isFinite(s.wakeVerificationThreshold) || s.wakeVerificationThreshold < 0.5 || s.wakeVerificationThreshold > 0.999) throw new Error('Invalid verification threshold');
  if (s.wakeCooldownMs < 200 || !Number.isFinite(s.wakeCooldownMs)) throw new Error('Unsafe wake cooldown');
  if (!Number.isInteger(s.maximumEvents) || s.maximumEvents < 1 || s.maximumEvents > 1000) throw new Error('Unsafe event buffer');
  if (s.mode === 'active' && !s.allowModelExecution) throw new Error('Active model mode requires explicit authorization');
  return s;
}
