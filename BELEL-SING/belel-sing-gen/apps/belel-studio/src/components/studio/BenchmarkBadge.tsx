"use client";

import React, { useMemo } from "react";
import type { Benchmark } from "@/lib/state/project.store";
import { cn } from "@/lib/utils/format";

export function BenchmarkBadge({ benchmark }: { benchmark?: Benchmark }) {
  const { label, cls } = useMemo(() => {
    if (!benchmark) return { label: "No Benchmark", cls: "bg-white/5 border-white/10 text-white/70" };

    if (benchmark.passed && benchmark.alignment_pending) {
      return { label: `⚠ Passed (Align Pending) · ${benchmark.score_10.toFixed(1)}`, cls: "bg-amber-500/15 border-amber-400/30 text-amber-100" };
    }
    if (benchmark.passed) {
      return { label: `✅ Passed · ${benchmark.score_10.toFixed(1)}`, cls: "bg-emerald-500/15 border-emerald-400/30 text-emerald-100" };
    }
    return { label: `❌ Failed · ${benchmark.score_10.toFixed(1)}`, cls: "bg-red-500/15 border-red-400/30 text-red-100" };
  }, [benchmark]);

  return (
    <span className={cn("px-2 py-1 rounded border text-xs", cls)}>
      {label}
    </span>
  );
}
