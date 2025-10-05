import { buildSystemPrompt } from "../system/prompts";
import cfg from "../config/gemini.config.json";
import { issueChallenge, verifySignature, keyFingerprintFromEnv } from "../guard/selfverify";

/**
 * The ONLY place Gemini SDK is invoked.
 * - Self-verifies via challenge/response (no secret exposure).
 * - Checks host allowlist (network policy should also enforce).
 * - Always prepends Concordium mandate to the system prompt.
 */
type AskOpts = { prompt: string; system?: string; options?: Record<string, unknown>; stream?: boolean; };

export async function callGemini(opts: AskOpts) {
  const challenge = issueChallenge();
  const signature = process.env.GEMINI_SIGNED_CHALLENGE || ""; // sidecar/KMS supplies this at call-time
  const verified = verifySignature(challenge, signature);
  if (!verified.ok) throw new Error("Gemini self-verification failed: " + (verified.reason ?? "unknown"));

  const allowed = new Set(cfg.network.geminiHosts);
  if (!allowed.has("generativelanguage.googleapis.com")) throw new Error("Gemini host not allowed");

  const sys = buildSystemPrompt(opts.system);

  // TODO: Replace stub with real Gemini SDK call using process.env.GEMINI_API_KEY
  return { text: `Simulated Gemini answer (guarded) for: ${opts.prompt}`, model: "gemini-1.5-pro", fingerprint: keyFingerprintFromEnv() };
}
