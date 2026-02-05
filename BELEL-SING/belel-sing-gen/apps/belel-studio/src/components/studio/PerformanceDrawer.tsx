"use client";

import React from "react";
import { Card } from "@/components/common/Card";
import { CodeBlock } from "@/components/common/CodeBlock";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "@/lib/api/client";
import { PerfLatestSchema } from "@/lib/api/contracts";

export function PerformanceDrawer() {
  const q = useQuery({
    queryKey: ["perf-latest"],
    queryFn: () => apiJson("/api/perf/latest", PerfLatestSchema),
    staleTime: 10_000
  });

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">Performance</div>
      <div className="text-xs text-white/60">
        Pulled from your perf claim runner output (FastAPI `/api/perf/latest`).
      </div>

      <Card className="p-3">
        <CodeBlock value={q.data ?? { loading: true }} />
      </Card>
    </div>
  );
}
