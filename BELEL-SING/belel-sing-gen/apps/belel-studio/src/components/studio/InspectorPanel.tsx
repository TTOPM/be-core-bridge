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
import { API } from "@/lib/api/routes";
import { apiJson } from "@/lib/api/client";
import { EditRequestSchema, EditResponseSchema } from "@/lib/api/contracts";

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
  const active = useProjectStore((s) => s.activeVersion());

  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{
    open: boolean;
    msg: string;
    v: "info" | "success" | "danger";
  }>({ open: false, msg: "", v: "info" });

  const header = useMemo(() => {
    if (tool === "repaint") return "Repaint (region regeneration)";
    if (tool === "extend") return "Extend (append + crossfade)";
    if (tool === "retake") return "Retake (full track)";
    return "Lyric Edit (text + optional repaint)";
  }, [tool]);

  const canRun = useMemo(() => {
    // Must have a source mel path to edit
    return Boolean(active?.mel_path);
  }, [active?.mel_path]);

  async function runEdit() {
    if (!projectId) throw new Error("projectId missing");
    if (!active?.mel_path) throw new Error("active mel_path missing (generate first)");
    setBusy(true);
    try {
      const payload = EditRequestSchema.parse({
        edit_type: tool,
        src_mel_pt: active.mel_path,
        src_wav: active.wav_path ?? null,
        prompt_override: null,
        lyrics_override: tool === "lyric_edit" ? lyricsDraft : null,
        start_sec: tool === "retake" ? null : sel.startSec,
        end_sec: tool === "retake" ? null : sel.endSec,
        extend_sec: tool === "extend" ? extendSec : null,
        strength,
        seed_delta: 17,
        attempt: 0,
        steps_override: stepsOverride,
        guidance_override: guidanceOverride,
        extra: {
          fade_sec: fadeSec,
          ui_tag: "belel-studio",
          title
        }
      });

      const res = await apiJson(API.edit, EditResponseSchema, {
        method: "POST",
        body: JSON.stringify(payload)
      });

      useProjectStore.getState().appendVersion({
        project_id: res.project_id,
        version_id: res.version_id,
        title,
        wav_path: res.wav_path,
        mel_path: res.mel_path,
        wav_sidecar: res.wav_sidecar,
        receipt: res.receipt,
        edit_id: res.edit_id,
        edit_type: res.edit_type,
        benchmark: res.benchmark
          ? {
              score_10: res.benchmark.score_10,
              passed: res.benchmark.passed,
              alignment_pending: res.benchmark.alignment_pending,
              gate_failures: res.benchmark.gate_failures
            }
          : { score_10: 0, passed: false },
        meta: res.meta ?? {}
      });

      setToast({ open: true, msg: `Edit complete: ${res.edit_type} → ${res.version_id}`, v: "success" });
    } catch (e: any) {
      setToast({ open: true, msg: e?.message ?? "edit failed", v: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-semibold">{header}</div>
        <div className="text-xs text-white/60 mt-1">
          Selection: {fmt2(sel.startSec)}s → {fmt2(sel.endSec)}s
        </div>
      </div>

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
            Text-only mode and alignment gate surfacing can be added once your backend returns alignment status.
          </div>
        </Card>
      ) : null}

      <Card className="p-3">
        <div className="text-xs text-white/60 mb-2">Run</div>
        <Button
          className="w-full disabled:opacity-40"
          disabled={!canRun || busy}
          onClick={runEdit}
        >
          {busy ? "Running..." : `Run ${tool}`}
        </Button>

        {!canRun ? (
          <div className="text-xs text-red-200/80 mt-2">
            No source mel_path on active version. Wire /generate next (Step 3) or select a generated version.
          </div>
        ) : null}
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
