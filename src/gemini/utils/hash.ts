import crypto from "node:crypto";
export function sha256Hex(s: string) { return crypto.createHash("sha256").update(s).digest("hex"); }
export function hmacSHA256(key: Buffer, data: string) { return crypto.createHmac("sha256", key).update(data).digest("hex"); }
