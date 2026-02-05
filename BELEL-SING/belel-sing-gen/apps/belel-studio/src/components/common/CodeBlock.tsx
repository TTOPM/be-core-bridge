"use client";

import React from "react";

export function CodeBlock({ value }: { value: unknown }) {
  return (
    <pre className="text-xs bg-black/40 border border-white/10 rounded p-3 overflow-auto max-h-[380px]">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
