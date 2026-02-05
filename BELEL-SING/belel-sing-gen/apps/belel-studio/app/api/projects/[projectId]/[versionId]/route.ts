import { NextRequest } from "next/server";
import { proxyJson } from "../../../_proxy";

export async function GET(
  req: NextRequest,
  ctx: { params: { projectId: string; versionId: string } }
) {
  const { projectId, versionId } = ctx.params;
  return proxyJson(req, `/api/receipt/${encodeURIComponent(projectId)}/${encodeURIComponent(versionId)}`);
}
