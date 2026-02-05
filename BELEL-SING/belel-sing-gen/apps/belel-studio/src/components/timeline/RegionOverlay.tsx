"use client";

import React, { useCallback, useMemo } from "react";
import { useSelectionStore } from "@/lib/state/selection.store";

type DragMode = "move" | "resize-left" | "resize-right";

function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

export function RegionOverlay({
  durationSec,
  containerRef,
}: {
  durationSec: number;
  containerRef: React.RefObject<HTMLDivElement>;
}) {
  const startSec = useSelectionStore((s) => s.startSec);
  const endSec = useSelectionStore((s) => s.endSec);
  const setSelection = useSelectionStore((s) => s.setSelection);
  const clearSelection = useSelectionStore((s) => s.clearSelection);

  const region = useMemo(() => {
    if (startSec == null || endSec == null) return null;
    const a = Math.min(startSec, endSec);
    const b = Math.max(startSec, endSec);
    if (b <= a) return null;
    return { a, b };
  }, [startSec, endSec]);

  const pxForSec = useCallback(
    (sec: number) => {
      const el = containerRef.current;
      if (!el) return 0;
      const w = el.clientWidth || 1;
      const d = Math.max(0.0001, durationSec || 0.0001);
      return (sec / d) * w;
    },
    [containerRef, durationSec]
  );

  const secForClientX = useCallback(
    (clientX: number) => {
      const el = containerRef.current;
      if (!el) return 0;
      const rect = el.getBoundingClientRect();
      const x = clamp(clientX - rect.left, 0, rect.width);
      const d = Math.max(0.0001, durationSec || 0.0001);
      return (x / Math.max(1, rect.width)) * d;
    },
    [containerRef, durationSec]
  );

  const beginDrag = useCallback(
    (mode: DragMode, e: React.PointerEvent) => {
      if (!region) return;
      e.preventDefault();
      e.stopPropagation();
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);

      const initA = region.a;
      const initB = region.b;
      const initX = e.clientX;

      const onMove = (ev: PointerEvent) => {
        const dxSec = secForClientX(ev.clientX) - secForClientX(initX);

        if (mode === "move") {
          const len = initB - initA;
          let na = initA + dxSec;
          let nb = na + len;
          if (na < 0) {
            na = 0;
            nb = len;
          }
          if (nb > durationSec) {
            nb = durationSec;
            na = nb - len;
          }
          setSelection(na, nb);
          return;
        }

        if (mode === "resize-left") {
          const na = clamp(initA + dxSec, 0, initB - 0.02);
          setSelection(na, initB);
          return;
        }

        if (mode === "resize-right") {
          const nb = clamp(initB + dxSec, initA + 0.02, durationSec);
          setSelection(initA, nb);
          return;
        }
      };

      const onUp = () => {
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
      };

      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    },
    [region, secForClientX, durationSec, setSelection]
  );

  if (!region) return null;

  const leftPx = pxForSec(region.a);
  const rightPx = pxForSec(region.b);
  const widthPx = Math.max(2, rightPx - leftPx);

  return (
    <div className="absolute inset-0 pointer-events-none">
      {/* dim outside */}
      <div
        className="absolute top-0 bottom-0 left-0 bg-black/40 pointer-events-none"
        style={{ width: leftPx }}
      />
      <div
        className="absolute top-0 bottom-0 bg-black/40 pointer-events-none"
        style={{ left: rightPx, right: 0 }}
      />

      {/* region */}
      <div
        className="absolute top-0 bottom-0 pointer-events-auto"
        style={{ left: leftPx, width: widthPx }}
      >
        <div
          className="absolute inset-0 rounded border border-white/25 bg-white/10"
          onDoubleClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            clearSelection();
          }}
          title="Drag to move. Double-click to clear."
        />

        {/* move handle (whole region) */}
        <div
          className="absolute inset-0 cursor-grab"
          onPointerDown={(e) => beginDrag("move", e)}
        />

        {/* left resize */}
        <div
          className="absolute top-0 bottom-0 left-0 w-2 cursor-ew-resize"
          onPointerDown={(e) => beginDrag("resize-left", e)}
          title="Resize start"
        />
        {/* right resize */}
        <div
          className="absolute top-0 bottom-0 right-0 w-2 cursor-ew-resize"
          onPointerDown={(e) => beginDrag("resize-right", e)}
          title="Resize end"
        />

        {/* label */}
        <div className="absolute top-2 left-2 text-[10px] text-white/80 bg-black/40 border border-white/10 rounded px-2 py-1">
          {region.a.toFixed(2)}s – {region.b.toFixed(2)}s
        </div>
      </div>
    </div>
  );
}
