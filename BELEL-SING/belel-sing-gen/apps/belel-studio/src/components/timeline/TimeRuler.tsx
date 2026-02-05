"use client";

import React, { useMemo } from "react";

export function TimeRuler({ seconds = 60 }: { seconds?: number }) {
  const marks = useMemo(() => {
    const arr: number[] = [];
    const step = seconds <= 60 ? 5 : 10;
    for (let t = 0; t <= seconds; t += step) arr.push(t);
    return arr;
  }, [seconds]);

  return (
    <div className="h-7 flex items-end gap-0 border-b border-white/10 bg-black/20 rounded-t">
      {marks.map((t) => (
        <div key={t} className="flex-1 relative">
          <div className="absolute left-0 bottom-0 h-3 w-px bg-white/15" />
          <div className="text-[10px] text-white/50 pl-1 pb-1">{t}s</div>
        </div>
      ))}
    </div>
  );
}
