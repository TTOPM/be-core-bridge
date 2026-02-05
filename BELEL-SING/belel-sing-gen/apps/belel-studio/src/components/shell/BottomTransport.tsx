"use client";

import React, { useMemo } from "react";
import { useSelectionStore } from "@/lib/state/selection.store";
import { useProjectStore } from "@/lib/state/project.store";
import { ABCompareToggle } from "@/components/studio/ABCompareToggle";
import { Button } from "@/components/common/Button";

export function BottomTransport() {
  const sel = useSelectionStore();
  const loop = useSelectionStore((s) => s.isLooping);
  const active = useProjectStore((s) => s.activeVersion());

  const selectionLabel = useMemo(() => {
    const a = sel.startSec.toFixed(2);
    const b = sel.endSec.toFixed(2);
    return `${a}s → ${b}s`;
  }, [sel.startSec, sel.endSec]);

  return (
    <footer className="h-16 border-t border-white/10 bg-black/45 px-4 flex items-center gap-3">
      <Button onClick={() => useProjectStore.getState().togglePlay()} variant="primary">
        Play/Pause
      </Button>

      <Button onClick={() => useSelectionStore.getState().toggleLoop()} variant="primary">
        Loop: {loop ? "ON" : "OFF"}
      </Button>

      <div className="text-xs text-white/60">
        Selection: <span className="text-white/80">{selectionLabel}</span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <ABCompareToggle />
        <div className="text-xs text-white/60">
          Active: <span className="text-white/80">{active?.version_id ?? "—"}</span>
        </div>
        <Button onClick={() => useProjectStore.getState().commitActive()} variant="primary">
          Commit Edit
        </Button>
      </div>
    </footer>
  );
}
