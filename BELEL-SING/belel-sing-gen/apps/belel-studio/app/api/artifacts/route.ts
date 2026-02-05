import { NextRequest } from "next/server";
import { proxyArtifact } from "../_proxy";

export async function GET(req: NextRequest) {
  const u = new URL(req.url);
  const path = u.searchParams.get("path");
  if (!path) return new Response("missing path", { status: 400 });

  // Forward query string exactly
  return proxyArtifact(req, `/api/artifacts?path=${encodeURIComponent(path)}`);
}
