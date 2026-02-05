import { NextRequest } from "next/server";
import { proxyJson } from "../_proxy";

export async function POST(req: NextRequest) {
  return proxyJson(req, "/api/generate");
}
