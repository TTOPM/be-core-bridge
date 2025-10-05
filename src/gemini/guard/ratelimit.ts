import cfg from "../config/gemini.config.json";
const bucket = new Map<string, { tokens: number; ts: number }>();
export function rateCheck(key: string) {
  const now = Date.now();
  const limit = cfg.rateLimit.tokensPerMinute;
  const burst = cfg.rateLimit.burst;
  const win = 60_000;
  const entry = bucket.get(key) ?? { tokens: limit * burst, ts: now };
  const refill = Math.floor((now - entry.ts) / win) * limit;
  entry.tokens = Math.min(entry.tokens + refill, limit * burst);
  entry.ts = now;
  if (entry.tokens <= 0) return false;
  entry.tokens -= 1000;
  bucket.set(key, entry);
  return true;
}
