/** Belel Acoustic Intelligence Network — additive sovereign contract v1.
 * No microphone capture, playback or permanent storage occurs in this module.
 */
export type BelelAcousticMode = 'off' | 'observe' | 'shadow' | 'active';
export type VoiceEngine = 'belel-fish' | 'belel-kokoro' | 'belel-elevenlabs' | 'belel-native' | 'moshi' | 'personaplex' | 'unknown';
export type AcousticEventName =
  | 'session.listening' | 'session.idle' | 'session.error'
  | 'wake.candidate' | 'wake.near_miss' | 'wake.verified' | 'wake.rejected'
  | 'speech.detected' | 'speech.transcript' | 'speech.pronunciation'
  | 'tts.started' | 'tts.ended' | 'tts.engine'
  | 'duplex.yield' | 'duplex.resume' | 'duplex.backchannel'
  | 'model.health' | 'network.health';
export interface AcousticEvent<T = Record<string, unknown>> {
  readonly schema: 'belel.acoustic.v1';
  readonly id: string;
  readonly type: AcousticEventName;
  readonly source: string;
  readonly at: number;
  readonly correlationId?: string;
  readonly payload: T;
}
export interface AcousticSettings {
  mode: BelelAcousticMode;
  /** Explicitly enables model access. No default external services. */
  allowModelExecution: boolean;
  /** Explicitly enables passing PCM to an independently configured model adapter. */
  allowAudioToModel: boolean;
  /** No raw-audio persistence is included; this only controls redacted metrics. */
  allowAggregateMetrics: boolean;
  wakePrimaryThreshold: number;
  wakeVerificationThreshold: number;
  wakeCooldownMs: number;
  maximumEvents: number;
}
export interface PCMFrame {
  readonly pcm: Float32Array;
  readonly sampleRate: number;
  readonly at: number;
  readonly source: 'existing-capture' | 'test-fixture';
}
export interface WakeScore {
  confidence: number;
  modelId: string;
  at: number;
}
export interface WakeResult {
  accepted: boolean;
  primary: WakeScore;
  verificationConfidence?: number;
  reason: 'accepted' | 'primary_low' | 'second_stage_failed' | 'cooldown' | 'near_miss' | 'inactive';
}
export interface AcousticModelProfile {
  id: string;
  family: 'moshi' | 'personaplex' | 'future-dessa' | 'other';
  capabilities: readonly string[];
  weightsLicense: string;
  requiresSeparateDeployment: boolean;
  approvedForProduction: boolean;
  officialUrl: string;
}
export interface DuplexModelEvent {
  kind: 'audio.delta' | 'transcript.delta' | 'turn.started' | 'turn.ended' | 'error' | 'health';
  /** PCM16LE, 24 kHz mono for local reference gateway; never auto-played. */
  audio?: Uint8Array;
  text?: string;
  detail?: string;
}
export interface DuplexModelAdapter {
  readonly id: string;
  readonly supportsDuplex: true;
  start(onEvent: (event: DuplexModelEvent) => void): Promise<void>;
  send(frame: PCMFrame): Promise<void>;
  stop(): Promise<void>;
}
