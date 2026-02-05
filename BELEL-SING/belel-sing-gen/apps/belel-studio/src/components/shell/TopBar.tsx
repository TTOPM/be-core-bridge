"use client";

import React from "react";
import { usePathname } from "next/navigation";

export function TopBar() {
  const pathname = usePathname();
  return (
    <header className="h-14 border-b border-white/10 bg-black/35 flex items-center px-4">
      <div className="text-xs text-white/60">{pathname}</div>
      <div className="ml-auto flex items-center gap-2 text-xs">
        <span className="px-2 py-1 rounded bg-white/5 border border-white/10 text-white/70">
          Deterministic IDs
        </span>
        <span className="px-2 py-1 rounded bg-white/5 border border-white/10 text-white/70">
          Receipts
        </span>
        <span className="px-2 py-1 rounded bg-white/5 border border-white/10 text-white/70">
          Gates
        </span>
      </div>
    </header>
  );
}
