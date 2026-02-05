"use client";

import React from "react";
import { useStudioStore, type EditTool } from "@/lib/state/studio.store";
import { cn } from "@/lib/utils/format";

function ToolButton({ t, label }: { t: EditTool; label: string }) {
  const tool = useStudioStore((s) => s.tool);
  const setTool = useStudioStore((s) => s.setTool);
  const active = tool === t;

  return (
    <button
      className={cn(
        "px-3 py-2 rounded border text-sm transition-colors",
        active
          ? "bg-white/10 border-white/10"
          : "bg-transparent border-white/10 hover:bg-white/5 text-white/80"
      )}
      onClick={() => setTool(t)}
    >
      {label}
    </button>
  );
}

export function ToolBar() {
  return (
    <div className="flex items-center gap-2">
      <ToolButton t="repaint" label="Repaint" />
      <ToolButton t="extend" label="Extend" />
      <ToolButton t="retake" label="Retake" />
      <ToolButton t="lyric_edit" label="Lyric Edit" />

      <div className="ml-auto text-xs text-white/60">
        Protocol UI: score · gate status · retries · receipt
      </div>
    </div>
  );
}
