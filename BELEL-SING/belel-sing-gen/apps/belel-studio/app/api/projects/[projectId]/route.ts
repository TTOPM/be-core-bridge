import { NextRequest } from "next/server";
import { proxyJson } from "../../_proxy";

export async function GET(req: NextRequest, ctx: { params: { projectId: string } }) {
  return proxyJson(req, `/api/projects/${encodeURIComponent(ctx.params.projectId)}`);
}
