"use client";

import React from "react";
import { Card } from "@/components/common/Card";

const LANGS: Array<{ code: string; name: string }> = [
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "pt", name: "Portuguese" }
];

export function LanguagePicker({
  value,
  onChange
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Card className="p-3">
      <div className="text-xs text-white/60 mb-2">Language</div>
      <select
        className="w-full px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code}>
            {l.name} ({l.code})
          </option>
        ))}
      </select>
      <div className="text-xs text-white/50 mt-2">
        Step 2 replaces this with live language_count_report.json via /api/lang/report with tier gating.
      </div>
    </Card>
  );
}
