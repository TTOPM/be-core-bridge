import { z } from "zod";

export const BenchmarkSchema = z.object({
  score_10: z.number(),
  passed: z.boolean(),
  breakdown: z.record(z.unknown()).optional().nullable(),
  alignment_pending: z.boolean().optional().nullable(),
  gate_failures: z.record(z.unknown()).optional().nullable(),
});

export const GenerateRequestSchema = z.object({
  prompt: z.string(),
  lyrics: z.string().default(""),
  duration_sec: z.number().int().min(1).max(600),
  language: z.string().default("en"),
  steps: z.number().int().min(1).max(50).optional().nullable(),
  guidance: z.number().min(0).max(50).optional().nullable(),
  seed: z.number().int().optional().nullable(),
  codec_ckpt: z.string().optional().nullable(),
  denoiser_ckpt: z.string().optional().nullable(),
  meta: z.record(z.unknown()).optional().nullable(),
});

export const GenerateResponseSchema = z.object({
  project_id: z.string(),
  version_id: z.string(),
  wav_path: z.string(),
  mel_path: z.string(),
  wav_sidecar: z.string(),
  meta: z.record(z.unknown()).optional().nullable(),
  benchmark: BenchmarkSchema.optional().nullable(),
});

export const EditRequestSchema = z.object({
  edit_type: z.enum(["repaint", "extend", "retake", "lyric_edit"]),
  src_mel_pt: z.string(),
  src_wav: z.string().optional().nullable(),
  prompt_override: z.string().optional().nullable(),
  lyrics_override: z.string().optional().nullable(),
  start_sec: z.number().optional().nullable(),
  end_sec: z.number().optional().nullable(),
  extend_sec: z.number().optional().nullable(),
  strength: z.number().min(0).max(1),
  seed_delta: z.number().int(),
  attempt: z.number().int(),
  steps_override: z.number().int().min(1).max(50).optional().nullable(),
  guidance_override: z.number().min(0).max(50).optional().nullable(),
  extra: z.record(z.unknown()).optional().nullable(),
});

export const EditResponseSchema = z.object({
  project_id: z.string(),
  version_id: z.string(),
  wav_path: z.string(),
  mel_path: z.string(),
  wav_sidecar: z.string(),
  receipt: z.string(),
  edit_id: z.string(),
  edit_type: z.string(),
  benchmark: BenchmarkSchema.optional().nullable(),
  meta: z.record(z.unknown()).optional().nullable(),
});

export const PerfLatestSchema = z.object({
  utc: z.string(),
  device: z.string(),
  dtype: z.string(),
  steps: z.number().int(),
  duration_sec: z.number().int(),
  e2e_sec: z.number(),
  codec_ckpt: z.string().optional().nullable(),
  denoiser_ckpt: z.string().optional().nullable(),
  claim: z.string(),
  raw: z.record(z.unknown()).optional().nullable(),
});

export const LangItemSchema = z.object({
  code: z.string(),
  name: z.string(),
  tier: z.enum(["stable", "experimental"]),
});

export const LangReportSchema = z.object({
  documented_count: z.number().int(),
  languages: z.array(LangItemSchema),
  gates: z.object({
    block_unsupported: z.boolean(),
    warn_experimental: z.boolean(),
  }),
});
