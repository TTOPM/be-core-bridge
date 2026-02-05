import { NextRequest, NextResponse } from "next/server";

function apiBase(): string {
  const v = process.env.BELEL_API_BASE;
  if (!v) throw new Error("BELEL_API_BASE is not set");
  return v.replace(/\/+$/, "");
}

export async function proxyJson(req: NextRequest, upstreamPath: string) {
  const base = apiBase();
  const url = `${base}${upstreamPath}`;

  const init: RequestInit = {
    method: req.method,
    headers: {
      "content-type": "application/json"
    }
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  const res = await fetch(url, init);
  const text = await res.text();

  return new NextResponse(text, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json"
    }
  });
}

export async function proxyArtifact(req: NextRequest, upstreamPathWithQuery: string) {
  const base = apiBase();
  const url = `${base}${upstreamPathWithQuery}`;

  // Pass through range headers for WAV seeking
  const headers: Record<string, string> = {};
  const range = req.headers.get("range");
  if (range) headers["range"] = range;

  const res = await fetch(url, { headers });
  const body = res.body;

  if (!body) {
    const text = await res.text().catch(() => "");
    return new NextResponse(text, { status: res.status });
  }

  const outHeaders = new Headers();
  const ct = res.headers.get("content-type");
  const cl = res.headers.get("content-length");
  const cr = res.headers.get("content-range");
  const ar = res.headers.get("accept-ranges");

  if (ct) outHeaders.set("content-type", ct);
  if (cl) outHeaders.set("content-length", cl);
  if (cr) outHeaders.set("content-range", cr);
  if (ar) outHeaders.set("accept-ranges", ar);

  return new NextResponse(body as any, { status: res.status, headers: outHeaders });
}
