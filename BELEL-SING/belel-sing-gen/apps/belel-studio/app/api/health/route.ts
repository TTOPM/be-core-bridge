import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ok: true,
    service: "belel-studio",
    utc: new Date().toISOString()
  });
}