"use client";

import React, { useMemo } from "react";
import { useSelectionStore } from "@/lib/state/selection.store";
import { clamp } from "@/lib/utils/format";

export function RegionOverlay({ totalSec = 60 }: { totalSec?: number }) {
  const start = useSelectionStore((s) => s.startSec);
  const end = useSelectionStore((s) => s.endSec);

  const leftPct = useMemo(() => clamp((start / totalSec) * 100, 0, 100), [start, totalSec]);
  const rightPct = useMemo(() => clamp((end / totalSec) * 100, 0, 100), [end, totalSec]);
  const widthPct = Math.max(0.5, rightPct - leftPct);

  return (
    <div className="absolute inset-0 pointer-events-none">
      <div
        className="absolute top-0 bottom-0 bg-emerald-500/10 border border-emerald-400/25"
        style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
      />
      <div className="absolute top-0 bottom-0 w-px bg-emerald-300/50" style={{ left: `${leftPct}%` }} />
      <div className="absolute top-0 bottom-0 w-px bg-emerald-300/50" style={{ left: `${rightPct}%` }} />
    </div>
  );
}
