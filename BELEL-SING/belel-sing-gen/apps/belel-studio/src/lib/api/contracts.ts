import { z } from "zod";

export const BenchmarkSchema = z.object({
  score_10: z.number(),
  passed: z.boolean(),
  alignment_pending: z.boolean().optional(),
  gate_failures: z.record(z.unknown()).optional()
});

export const VersionSchema = z.object({
  project_id: z.string(),
  version_id: z.string(),
  wav_path: z.string().optional(),
  mel_path: z.string().optional(),
  wav_sidecar: z.string().optional(),
  receipt: z.string().optional(),
  edit_id: z.string().optional(),
  edit_type: z.string().optional(),
  meta: z.record(z.unknown()).optional(),
  benchmark: BenchmarkSchema.optional()
});

export const GenerateRequestSchema = z.object({
  prompt: z.string(),
  lyrics: z.string().optional().default(""),
  duration_sec: z.number(),
  language: z.string().default("en"),
  steps: z.number().int().optional(),
  guidance: z.number().optional(),
  seed: z.number().int().optional(),
  meta: z.record(z.unknown()).optional()
});

export const GenerateResponseSchema = z.object({
  project_id: z.string(),
  version_id: z.string(),
  wav_path: z.string(),
  mel_path: z.string(),
  wav_sidecar: z.string(),
  meta: z.record(z.unknown()).optional(),
  benchmark: BenchmarkSchema.optional()
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
  seed_delta: z.number().int().default(0),
  attempt: z.number().int().default(0),
  steps_override: z.union([z.literal(2), z.literal(4), z.literal(6)]).optional().nullable(),
  guidance_override: z.number().optional().nullable(),
  extra: z.record(z.unknown()).optional().nullable()
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
  benchmark: BenchmarkSchema.optional(),
  meta: z.record(z.unknown()).optional()
});

export const LangReportSchema = z.object({
  documented_count: z.number(),
  languages: z.array(
    z.object({
      code: z.string(),
      name: z.string(),
      tier: z.enum(["stable", "experimental"]).default("stable")
    })
  ),
  gates: z.object({
    block_unsupported: z.boolean(),
    warn_experimental: z.boolean()
  })
});

export const PerfLatestSchema = z.object({
  utc: z.string(),
  device: z.string(),
  dtype: z.string(),
  steps: z.number(),
  duration_sec: z.number(),
  e2e_sec: z.number(),
  claim: z.string(),
  raw: z.record(z.unknown()).optional()
});
