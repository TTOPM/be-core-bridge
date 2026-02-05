import { NextRequest } from "next/server";
import { proxyJson } from "../../_proxy";

export async function GET(req: NextRequest) {
  return proxyJson(req, "/api/perf/latest");
}
