"use client";

import React, { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { Slider } from "@/components/common/Slider";
import { Button } from "@/components/common/Button";
import { useStudioStore } from "@/lib/state/studio.store";
import { useSelectionStore } from "@/lib/state/selection.store";
import { useProjectStore } from "@/lib/state/project.store";
import { fmt2 } from "@/lib/utils/format";
import { Toast } from "@/components/common/Toast";

export function InspectorPanel() {
  const tool = useStudioStore((s) => s.tool);
  const strength = useStudioStore((s) => s.strength);
  const fadeSec = useStudioStore((s) => s.fadeSec);
  const stepsOverride = useStudioStore((s) => s.stepsOverride);
  const guidanceOverride = useStudioStore((s) => s.guidanceOverride);
  const extendSec = useStudioStore((s) => s.extendSec);
  const lyricsDraft = useStudioStore((s) => s.lyricsDraft);

  const setStrength = useStudioStore((s) => s.setStrength);
  const setFadeSec = useStudioStore((s) => s.setFadeSec);
  const setStepsOverride = useStudioStore((s) => s.setStepsOverride);
  const setGuidanceOverride = useStudioStore((s) => s.setGuidanceOverride);
  const setExtendSec = useStudioStore((s) => s.setExtendSec);
  const setLyricsDraft = useStudioStore((s) => s.setLyricsDraft);

  const sel = useSelectionStore();
  const projectId = useProjectStore((s) => s.projectId);
  const title = useProjectStore((s) => s.title);

  const [toast, setToast] = useState<{ open: boolean; msg: string; v: "info" | "success" | "danger" }>(
    { open: false, msg: "", v: "info" }
  );

  const header = useMemo(() => {
    if (tool === "repaint") return "Repaint (region regeneration)";
    if (tool === "extend") return "Extend (append + crossfade)";
    if (tool === "retake") return "Retake (full track)";
    return "Lyric Edit (text + optional repaint)";
  }, [tool]);

  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-semibold">{header}</div>
        <div className="text-xs text-white/60 mt-1">
          Selection: {fmt2(sel.startSec)}s → {fmt2(sel.endSec)}s
        </div>
      </div>

      {/* Shared controls */}
      <Card className="p-3 space-y-3">
        <div className="text-xs text-white/60">Strength ({fmt2(strength)})</div>
        <Slider value={strength} min={0.05} max={1} step={0.01} onChange={setStrength} />

        <div className="text-xs text-white/60">Fade (sec) ({fmt2(fadeSec)})</div>
        <Slider value={fadeSec} min={0} max={0.25} step={0.01} onChange={setFadeSec} />

        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-white/60 mb-1">Steps</div>
            <select
              className="w-full px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
              value={stepsOverride}
              onChange={(e) => setStepsOverride(parseInt(e.target.value, 10) as 2 | 4 | 6)}
            >
              <option value={2}>2</option>
              <option value={4}>4</option>
              <option value={6}>6</option>
            </select>
          </div>
          <div>
            <div className="text-xs text-white/60 mb-1">Guidance</div>
            <input
              className="w-full px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
              value={guidanceOverride}
              onChange={(e) => setGuidanceOverride(parseFloat(e.target.value || "0"))}
            />
          </div>
        </div>
      </Card>

      {/* Tool-specific */}
      {tool === "extend" ? (
        <Card className="p-3 space-y-2">
          <div className="text-xs text-white/60">Extend seconds</div>
          <input
            className="w-full px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
            value={extendSec}
            onChange={(e) => setExtendSec(parseFloat(e.target.value || "0"))}
          />
          <div className="flex gap-2">
            <Button onClick={() => setExtendSec(15)}>+15</Button>
            <Button onClick={() => setExtendSec(30)}>+30</Button>
            <Button onClick={() => setExtendSec(60)}>+60</Button>
          </div>
        </Card>
      ) : null}

      {tool === "lyric_edit" ? (
        <Card className="p-3 space-y-2">
          <div className="text-xs text-white/60">Lyrics draft</div>
          <textarea
            className="w-full min-h-[160px] px-3 py-2 rounded border border-white/10 bg-black/30 text-sm"
            value={lyricsDraft}
            onChange={(e) => setLyricsDraft(e.target.value)}
          />
          <div className="text-xs text-white/50">
            Step 2 will wire: text-only (no audio change) vs apply-to-region (repaint conditioned on lyrics).
          </div>
        </Card>
      ) : null}

      {/* Run action */}
      <Card className="p-3">
        <div className="text-xs text-white/60 mb-2">Run</div>
        <Button
          className="w-full"
          onClick={() => {
            // Step 1: we record an attempted run in history (no backend yet)
            const idx = useProjectStore.getState().versions.length;
            useProjectStore.getState().appendVersion({
              project_id: projectId ?? "unknown",
              version_id: `v${idx}`,
              title,
              edit_type: tool,
              benchmark: { score_10: 0, passed: false, alignment_pending: true }
            });
            setToast({ open: true, msg: `Queued ${tool} (backend wiring is Step 2).`, v: "info" });
          }}
        >
          Run {tool}
        </Button>
        <div className="text-xs text-white/50 mt-2">
          Step 2 replaces this with POST /api/edit → receipt + benchmark + artifacts.
        </div>
      </Card>

      <Toast
        open={toast.open}
        message={toast.msg}
        variant={toast.v}
        onClose={() => setToast({ open: false, msg: "", v: "info" })}
      />
    </div>
  );
}
