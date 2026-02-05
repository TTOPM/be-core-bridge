"use client";

import React from "react";
import { cn } from "@/lib/utils/format";

export function Tabs({
  tabs,
  active,
  onChange
}: {
  tabs: string[];
  active: string;
  onChange: (t: string) => void;
}) {
  return (
    <div className="flex gap-2 border border-white/10 bg-black/25 rounded p-1">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={cn(
            "px-3 py-1.5 rounded text-xs border",
            t === active
              ? "bg-white/10 border-white/10"
              : "bg-transparent hover:bg-white/5 border-transparent text-white/70"
          )}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
