"use client";

import React from "react";
import { Card } from "@/components/common/Card";

export function StylePromptBox({
  value,
  onChange
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Card className="p-3">
      <div className="text-xs text-white/60 mb-2">Style / prompt</div>
      <textarea
        className="w-full min-h-[120px] px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Describe the sound: voice, genre, instrumentation, pacing, mix..."
      />
    </Card>
  );
}
