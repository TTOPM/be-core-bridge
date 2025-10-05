import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import cfg from "../config/gemini.config.json";

export type VerifyResult = { ok: boolean; reason?: string; fingerprint?: string };

export function keyFingerprintFromEnv(): string {
  const raw = process.env.GEMINI_API_KEY || "unset";
  const hash = crypto.createHash("sha256").update(raw).digest("hex");
  return `gk_${hash.slice(0,12)}`;
}

export function loadPubKey() {
  try { return fs.readFileSync(path.resolve(cfg.signing.pubKeyPath), "utf8"); }
  catch { return null; }
}

export function issueChallenge(): string {
  return crypto.randomBytes(32).toString("hex");
}

export function verifySignature(challenge: string, signatureB64: string): VerifyResult {
  try {
    const pub = loadPubKey();
    if (!pub) return { ok: false, reason: "no_public_key" };
    const verifier = crypto.createVerify("SHA256");
    verifier.update(challenge); verifier.end();
    const ok = verifier.verify(pub, Buffer.from(signatureB64, "base64"));
    if (!ok) return { ok: false, reason: "bad_signature" };
    const fp = keyFingerprintFromEnv();
    return { ok: true, fingerprint: fp };
  } catch (e:any) {
    return { ok: false, reason: e?.message || "verify_error" };
  }
}
