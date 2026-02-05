"use client";

import React, { useMemo, useState } from "react";
import { WaveformTimeline } from "@/components/timeline/WaveformTimeline";
import { ToolBar } from "@/components/studio/ToolBar";
import { InspectorPanel } from "@/components/studio/InspectorPanel";
import { RunHistoryList } from "@/components/studio/RunHistoryList";
import { ReceiptViewer } from "@/components/studio/ReceiptViewer";
import { PerformanceDrawer } from "@/components/studio/PerformanceDrawer";
import { BenchmarkBadge } from "@/components/studio/BenchmarkBadge";
import { useProjectStore } from "@/lib/state/project.store";

type RightTab = "tools" | "runs" | "receipt" | "perf";

function Pill({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="px-2.5 py-1.5 rounded border border-white/10 bg-black/30">
      <div className="text-[10px] text-white/50 leading-none">{label}</div>
      <div className="text-xs text-white/80 leading-none mt-1">{value}</div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "px-3 py-2 text-xs rounded border transition",
        active
          ? "border-white/20 bg-white/10 text-white"
          : "border-white/10 bg-black/20 text-white/60 hover:text-white/80 hover:border-white/15",
      ].join(" ")}
      type="button"
    >
      {children}
    </button>
  );
}

export function StudioShell() {
  const projectId = useProjectStore((s) => s.projectId);
  const title = useProjectStore((s) => s.title);
  const versions = useProjectStore((s) => s.versions);
  const active = useProjectStore((s) => s.activeVersion());
  const setActiveVersion = useProjectStore((s) => s.setActiveVersion);

  const [tab, setTab] = useState<RightTab>("tools");

  const activeBenchmark = active?.benchmark ?? null;
  const score = typeof activeBenchmark?.score_10 === "number" ? activeBenchmark.score_10 : null;
  const passed = typeof activeBenchmark?.passed === "boolean" ? activeBenchmark.passed : null;
  const alignmentPending = (activeBenchmark as any)?.alignment_pending ?? null;

  const statusChip = useMemo(() => {
    if (!activeBenchmark) return { label: "No Protocol", cls: "bg-black/20 border-white/10 text-white/60" };
    if (passed === true && alignmentPending) return { label: "Passed (Alignment Pending)", cls: "bg-yellow-500/10 border-yellow-500/30 text-yellow-200" };
    if (passed === true) return { label: "Passed", cls: "bg-emerald-500/10 border-emerald-500/30 text-emerald-200" };
    if (passed === false) return { label: "Gate Failed", cls: "bg-red-500/10 border-red-500/30 text-red-200" };
    return { label: "Protocol Unknown", cls: "bg-black/20 border-white/10 text-white/60" };
  }, [activeBenchmark, passed, alignmentPending]);

  // Empty state: no project loaded yet (e.g., hard refresh still loading)
  if (!projectId) {
    return (
      <div className="p-4 pb-24">
        <div className="rounded border border-white/10 bg-black/30 p-6">
          <div className="text-sm font-semibold">Loading Studio…</div>
          <div className="text-xs text-white/60 mt-2">
            If this persists, open <span className="text-white/80">Create</span> and generate a track.
          </div>
        </div>
      </div>
    );
  }

  // Another empty state: project exists but no versions
  if (!versions || versions.length === 0) {
    return (
      <div className="p-4 pb-24">
        <div className="rounded border border-white/10 bg-black/30 p-6">
          <div className="text-sm font-semibold">No versions in this project</div>
          <div className="text-xs text-white/60 mt-2">
            Generate a track in <span className="text-white/80">Create</span> to begin.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 pb-24 space-y-4">
      {/* Header */}
      <div className="rounded border border-white/10 bg-black/30 p-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <div className="text-[11px] text-white/50">Belel Studio</div>
            <div className="text-base font-semibold leading-tight">
              {title?.trim() ? title : "Untitled"}
            </div>
            <div className="text-xs text-white/60">
              Project: <span className="text-white/80">{projectId}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <Pill label="Active Version" value={active?.version_id ?? "none"} />
            <Pill label="Protocol Score" value={score !== null ? score.toFixed(2) : "—"} />
            <div className={["px-2.5 py-2 rounded border text-xs", statusChip.cls].join(" ")}>
              {statusChip.label}
            </div>

            <div className="min-w-[220px]">
              <div className="text-[10px] text-white/50 mb-1">Versions</div>
              <select
                className="w-full px-3 py-2 rounded border border-white/10 bg-black/20 text-xs"
                value={active?.version_id ?? ""}
                onChange={(e) => setActiveVersion(e.target.value)}
              >
                {versions.map((v) => (
                  <option key={v.version_id} value={v.version_id}>
                    {v.version_id} {v.edit_type ? `• ${v.edit_type}` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Canvas */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
          <div className="rounded border border-white/10 bg-black/30 p-3">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">Timeline</div>
              <div className="text-xs text-white/60">
                Select a region → run <span className="text-white/80">Repaint</span> / <span className="text-white/80">Extend</span> / <span className="text-white/80">Retake</span> / <span className="text-white/80">Lyric Edit</span>
              </div>
            </div>

            <ToolBar />
            <div className="mt-4">
              <WaveformTimeline />
            </div>
          </div>

          <div className="rounded border border-white/10 bg-black/30 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-semibold">Quality</div>
              <div className="text-xs text-white/60">Protocol badge reflects the active version.</div>
            </div>
            <BenchmarkBadge />
          </div>
        </div>

        {/* Inspector */}
        <div className="col-span-12 lg:col-span-4">
          <div className="lg:sticky lg:top-4 space-y-3">
            <div className="rounded border border-white/10 bg-black/30 p-3">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">Inspector</div>
                <div className="text-xs text-white/60">Proof-native editing</div>
              </div>

              <div className="flex flex-wrap gap-2 mb-3">
                <TabButton active={tab === "tools"} onClick={() => setTab("tools")}>
                  Tools
                </TabButton>
                <TabButton active={tab === "runs"} onClick={() => setTab("runs")}>
                  Runs
                </TabButton>
                <TabButton active={tab === "receipt"} onClick={() => setTab("receipt")}>
                  Receipt
                </TabButton>
                <TabButton active={tab === "perf"} onClick={() => setTab("perf")}>
                  Performance
                </TabButton>
              </div>

              {tab === "tools" ? (
                <InspectorPanel />
              ) : null}

              {tab === "runs" ? (
                <RunHistoryList />
              ) : null}

              {tab === "receipt" ? (
                <ReceiptViewer />
              ) : null}

              {tab === "perf" ? (
                <PerformanceDrawer />
              ) : null}
            </div>

            <div className="rounded border border-white/10 bg-black/20 p-3">
              <div className="text-xs text-white/60">
                Studio discipline:
              </div>
              <ul className="text-xs text-white/70 list-disc ml-5 mt-2 space-y-1">
                <li>Edits are deterministic (stable <span className="text-white/80">edit_id</span>).</li>
                <li>Receipts are written for every run (provenance chain).</li>
                <li>Protocol gates enforce artifact-free output.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
