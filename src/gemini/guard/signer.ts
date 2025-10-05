import crypto from "node:crypto";
import fs from "node:fs";
import cfg from "../config/gemini.config.json";
export function signManifest(manifest: object) {
  if (!cfg.signing?.enabled) return { manifest, signature: null };
  try {
    const priv = fs.readFileSync(cfg.signing.privKeyPath, "utf8");
    const signer = crypto.createSign("SHA256");
    const payload = JSON.stringify(manifest);
    signer.update(payload); signer.end();
    const sig = signer.sign(priv, "base64");
    return { manifest, signature: sig };
  } catch {
    return { manifest, signature: null };
  }
}
