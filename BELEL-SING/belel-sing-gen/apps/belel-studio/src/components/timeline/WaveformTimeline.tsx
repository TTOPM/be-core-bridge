"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";
import { Card } from "@/components/common/Card";
import { TimeRuler } from "@/components/timeline/TimeRuler";
import { RegionOverlay } from "@/components/timeline/RegionOverlay";
import { useSelectionStore } from "@/lib/state/selection.store";
import { clamp, fmt2 } from "@/lib/utils/format";

export function WaveformTimeline() {
  const totalSec = 60;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [dragAnchorSec, setDragAnchorSec] = useState<number | null>(null);

  const start = useSelectionStore((s) => s.startSec);
  const end = useSelectionStore((s) => s.endSec);
  const setSelection = useSelectionStore((s) => s.setSelection);

  const selectionLabel = useMemo(() => `${fmt2(start)}s → ${fmt2(end)}s`, [start, end]);

  const pxToSec = useCallback(
    (clientX: number) => {
      const el = containerRef.current;
      if (!el) return 0;
      const r = el.getBoundingClientRect();
      const x = clamp(clientX - r.left, 0, r.width);
      const pct = r.width > 0 ? x / r.width : 0;
      return clamp(pct * totalSec, 0, totalSec);
    },
    [totalSec]
  );

  const onDown = useCallback(
    (e: React.MouseEvent) => {
      const sec = pxToSec(e.clientX);
      setDragging(true);
      setDragAnchorSec(sec);
      setSelection(sec, sec + 0.5);
    },
    [pxToSec, setSelection]
  );

  const onMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || dragAnchorSec === null) return;
      const sec = pxToSec(e.clientX);
      setSelection(dragAnchorSec, sec);
    },
    [dragging, dragAnchorSec, pxToSec, setSelection]
  );

  const onUp = useCallback(() => {
    setDragging(false);
    setDragAnchorSec(null);
  }, []);

  return (
    <div className="space-y-2">
      <div className="text-xs text-white/60">Waveform</div>
      <Card className="overflow-hidden">
        <TimeRuler seconds={totalSec} />
        <div
          ref={containerRef}
          className="relative h-[140px] bg-black/25"
          onMouseDown={onDown}
          onMouseMove={onMove}
          onMouseUp={onUp}
          onMouseLeave={onUp}
        >
          {/* Minimal “waveform-like” grid so the studio reads as a DAW even before audio loads */}
          <div className="absolute inset-0 opacity-60">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="absolute top-0 bottom-0 w-px bg-white/10"
                style={{ left: `${(i / 12) * 100}%` }}
              />
            ))}
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="absolute left-0 right-0 h-px bg-white/10"
                style={{ top: `${(i / 6) * 100}%` }}
              />
            ))}
          </div>

          <RegionOverlay totalSec={totalSec} />

          <div className="absolute bottom-2 right-2 text-[11px] text-white/60 bg-black/40 px-2 py-1 rounded border border-white/10">
            {selectionLabel}
          </div>
        </div>
      </Card>

      <div className="text-[11px] text-white/50">
        Drag to select a region. Step 2 will draw real waveform from WAV via /api/artifacts with range support.
      </div>
    </div>
  );
}
