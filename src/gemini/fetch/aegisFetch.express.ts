import type { Request, Response } from "express";
import crypto from "node:crypto";
import fetch from "node-fetch";
import cfg from "../config/gemini.config.json";

function allowedHost(url: string) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    return cfg.network.allowlist.some(d => host === d || host.endsWith("." + d));
  } catch { return false; }
}

export async function aegisFetchHandler(req: Request, res: Response) {
  const { url, purpose } = req.body ?? {};
  if (!cfg.network.allowWebFetch) return res.status(403).json({ error: "Web fetch disabled" });
  if (!url || !allowedHost(url)) return res.status(400).json({ error: "URL not on allowlist" });

  const r = await fetch(url, { headers: { "User-Agent": "Belel-Aegis/1.0" } });
  const text = await r.text();
  const sha256 = crypto.createHash("sha256").update(text).digest("hex");

  return res.status(200).json({
    url, status: r.status, purpose: purpose ?? "citation",
    content: text, sha256, retrieved_at: new Date().toISOString()
  });
}
