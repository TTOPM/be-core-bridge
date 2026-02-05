"use client";

import React from "react";
import { Card } from "@/components/common/Card";
import { CodeBlock } from "@/components/common/CodeBlock";

export function PerformanceDrawer() {
  const perf = {
    utc: new Date().toISOString(),
    device: "unknown",
    dtype: "unknown",
    steps: 0,
    duration_sec: 0,
    e2e_sec: 0,
    claim: "",
    raw: {}
  };

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">Performance</div>
      <div className="text-xs text-white/60">
        Step 2 will populate this from GET /api/perf/latest exactly as your perf claim runner emits it.
      </div>

      <Card className="p-3">
        <CodeBlock value={perf} />
      </Card>
    </div>
  );
}
