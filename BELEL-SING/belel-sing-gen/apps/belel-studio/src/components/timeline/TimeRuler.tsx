"use client";

import React, { useMemo } from "react";

function formatTime(sec: number) {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  const r = s - m * 60;
  const ss = Math.floor(r);
  const ms = Math.floor((r - ss) * 1000);
  return `${m}:${String(ss).padStart(2, "0")}.${String(Math.floor(ms / 10)).padStart(2, "0")}`;
}

export function TimeRuler({
  durationSec,
  width,
}: {
  durationSec: number;
  width: number;
}) {
  const ticks = useMemo(() => {
    const d = Math.max(0, durationSec || 0);
    const w = Math.max(1, width || 1);

    // choose tick spacing by duration
    const major =
      d <= 30 ? 5 :
      d <= 120 ? 10 :
      d <= 300 ? 30 :
      60;

    const minor = major / 5;

    const out: { x: number; major: boolean; label?: string }[] = [];
    const step = minor;

    for (let t = 0; t <= d + 1e-6; t += step) {
      const x = (t / d) * w;
      const isMajor = Math.abs((t / major) - Math.round(t / major)) < 1e-6;
      out.push({ x, major: isMajor, label: isMajor ? formatTime(t) : undefined });
    }
    return out;
  }, [durationSec, width]);

  return (
    <div className="w-full h-8 relative select-none">
      {ticks.map((tk, i) => (
        <div key={i} className="absolute top-0" style={{ left: tk.x }}>
          <div className={tk.major ? "h-4 w-px bg-white/25" : "h-2 w-px bg-white/15"} />
          {tk.label ? (
            <div className="text-[10px] text-white/45 mt-1 -translate-x-1/2 whitespace-nowrap">
              {tk.label}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
