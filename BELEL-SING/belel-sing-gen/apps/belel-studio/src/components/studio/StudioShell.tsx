"use client";

import React, { useMemo, useState } from "react";
import { useStudioStore } from "@/lib/state/studio.store";
import { useProjectStore } from "@/lib/state/project.store";

function clsStatus(s: string) {
  if (s === "completed") return "bg-emerald-500/10 border-emerald-500/30 text-emerald-200";
  if (s === "running") return "bg-blue-500/10 border-blue-500/30 text-blue-200";
  if (s === "failed") return "bg-red-500/10 border-red-500/30 text-red-200";
  return "bg-white/5 border-white/10 text-white/70";
}

function clsPass(passed?: boolean, pending?: boolean) {
  if (passed === true && pending) return "bg-yellow-500/10 border-yellow-500/30 text-yellow-200";
  if (passed === true) return "bg-emerald-500/10 border-emerald-500/30 text-emerald-200";
  if (passed === false) return "bg-red-500/10 border-red-500/30 text-red-200";
  return "bg-white/5 border-white/10 text-white/60";
}

function clsKind(kind?: string) {
  if (kind === "edit") return "bg-purple-500/10 border-purple-500/30 text-purple-200";
  if (kind === "generate") return "bg-cyan-500/10 border-cyan-500/30 text-cyan-200";
  return "bg-white/5 border-white/10 text-white/60";
}

function pillBase() {
  return "px-2 py-1 rounded border text-[10px] leading-none";
}

function safeJson(obj: any, limit = 18000): string {
  try {
    const s = JSON.stringify(obj, null, 2);
    if (s.length <= limit) return s;
    return s.slice(0, limit) + "\n…(truncated)…";
  } catch {
    return String(obj ?? "");
  }
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-3">
      <div className="text-[10px] uppercase tracking-wide text-white/50 mb-1">{title}</div>
      <div className="rounded border border-white/10 bg-black/20 p-2">{children}</div>
    </div>
  );
}

function CodeBox({ value }: { value: any }) {
  const text = useMemo(() => safeJson(value), [value]);
  return (
    <pre className="text-[10px] text-white/70 overflow-auto max-h-56 whitespace-pre-wrap break-words">
      {text}
    </pre>
  );
}

function GatePills({
  gate_failures,
}: {
  gate_failures?: Record<string, number>;
}) {
  const items = useMemo(() => {
    if (!gate_failures) return [];
    return Object.entries(gate_failures)
      .map(([k, v]) => ({ k, v: Number(v) }))
      // heuristic ordering: show “most severe” first
      .sort((a, b) => Math.abs(b.v) - Math.abs(a.v));
  }, [gate_failures]);

  if (!items.length) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {items.map(({ k, v }) => (
        <span
          key={k}
          className="px-2 py-1 rounded border border-red-500/25 bg-red-500/10 text-[10px] text-red-200"
          title={`${k}=${v}`}
        >
          {k}={v.toFixed(4)}
        </span>
      ))}
    </div>
  );
}

export function RunHistoryList() {
  const runs = useStudioStore((s) => s.runs);
  const activeVersionId = useProjectStore((s) => s.activeVersion()?.version_id);
  const setActiveVersion = useProjectStore((s) => s.setActiveVersion);

  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setOpen((m) => ({ ...m, [id]: !m[id] }));

  if (!runs || runs.length === 0) {
    return (
      <div className="rounded border border-white/10 bg-black/20 p-3 text-xs text-white/60">
        No runs yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {runs.map((r) => {
        const isActive = Boolean(r.version_id && r.version_id === activeVersionId);
        const isOpen = Boolean(open[r.run_id]);

        // best-effort extractors (don’t break if response schema varies)
        const response: any = r.response ?? {};
        const receiptPath =
          typeof response?.receipt === "string" ? response.receipt : undefined;
        const editId =
          typeof response?.edit_id === "string" ? response.edit_id : undefined;
        const claim =
          typeof response?.claim === "string" ? response.claim : undefined;

        return (
          <div
            key={r.run_id}
            className={[
              "rounded border p-3 transition",
              isActive
                ? "border-white/25 bg-white/10"
                : "border-white/10 bg-black/20 hover:border-white/15",
            ].join(" ")}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div className="text-xs font-semibold truncate">{r.label}</div>

                  <span className={[pillBase(), clsKind(r.kind)].join(" ")}>
                    {(r.kind ?? "run").toUpperCase()}
                  </span>

                  {r.tool ? (
                    <span className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                      {r.tool}
                    </span>
                  ) : null}

                  {isActive ? (
                    <span className={[pillBase(), "border-white/20 bg-white/10 text-white"].join(" ")}>
                      ACTIVE
                    </span>
                  ) : null}
                </div>

                <div className="text-[10px] text-white/50 mt-1">
                  {r.utc}
                  {r.version_id ? ` • ${r.version_id}` : ""}
                  {r.project_id ? ` • ${r.project_id}` : ""}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className={[pillBase(), clsStatus(r.status)].join(" ")}>
                  {r.status.toUpperCase()}
                </div>

                <button
                  type="button"
                  onClick={() => toggle(r.run_id)}
                  className={[
                    pillBase(),
                    "border-white/10 bg-black/20 text-white/70 hover:text-white/90 hover:border-white/15",
                  ].join(" ")}
                >
                  {isOpen ? "HIDE" : "DETAILS"}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-2">
              <div className={[pillBase(), clsPass(r.passed, r.alignment_pending)].join(" ")}>
                {r.passed === true && r.alignment_pending
                  ? "PASSED (ALIGN PENDING)"
                  : r.passed === true
                    ? "PASSED"
                    : r.passed === false
                      ? "GATE FAILED"
                      : "NO PROTOCOL"}
              </div>

              <div className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                Score: {typeof r.score_10 === "number" ? r.score_10.toFixed(2) : "—"}
              </div>

              <div className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                Retries: {typeof r.retries_used === "number" ? r.retries_used : "—"}/
                {typeof r.retries_max === "number" ? r.retries_max : "—"}
              </div>

              {typeof r.e2e_sec === "number" ? (
                <div className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                  E2E: {r.e2e_sec.toFixed(2)}s
                </div>
              ) : null}

              {/* Quick actions */}
              {r.version_id ? (
                <button
                  type="button"
                  onClick={() => setActiveVersion(r.version_id!)}
                  className={[
                    pillBase(),
                    "border-white/10 bg-black/20 text-white/70 hover:text-white/90 hover:border-white/15",
                  ].join(" ")}
                  title="Set this version as active"
                >
                  SET ACTIVE
                </button>
              ) : null}

              {receiptPath ? (
                <button
                  type="button"
                  onClick={() => copyToClipboard(receiptPath)}
                  className={[
                    pillBase(),
                    "border-white/10 bg-black/20 text-white/70 hover:text-white/90 hover:border-white/15",
                  ].join(" ")}
                  title="Copy receipt path"
                >
                  COPY RECEIPT
                </button>
              ) : null}

              {editId ? (
                <button
                  type="button"
                  onClick={() => copyToClipboard(editId)}
                  className={[
                    pillBase(),
                    "border-white/10 bg-black/20 text-white/70 hover:text-white/90 hover:border-white/15",
                  ].join(" ")}
                  title="Copy edit_id"
                >
                  COPY EDIT_ID
                </button>
              ) : null}

              {claim ? (
                <button
                  type="button"
                  onClick={() => copyToClipboard(claim)}
                  className={[
                    pillBase(),
                    "border-white/10 bg-black/20 text-white/70 hover:text-white/90 hover:border-white/15",
                  ].join(" ")}
                  title="Copy performance claim"
                >
                  COPY CLAIM
                </button>
              ) : null}
            </div>

            <GatePills gate_failures={r.gate_failures} />

            {r.status === "failed" && r.error ? (
              <div className="mt-2 text-[10px] text-red-200/90">
                Error: <span className="text-red-200/80">{r.error}</span>
              </div>
            ) : null}

            {isOpen ? (
              <div className="mt-3">
                {/* breakdown */}
                {r.response?.benchmark?.breakdown || r.response?.benchmark ? (
                  <Section title="Protocol Breakdown">
                    <CodeBox value={r.response?.benchmark?.breakdown ?? r.response?.benchmark} />
                  </Section>
                ) : null}

                {/* request/response */}
                <div className="grid grid-cols-1 gap-3 mt-3">
                  {r.request ? (
                    <Section title="Request">
                      <CodeBox value={r.request} />
                    </Section>
                  ) : null}

                  {r.response ? (
                    <Section title="Response">
                      <CodeBox value={r.response} />
                    </Section>
                  ) : null}
                </div>

                {/* quick metadata */}
                <div className="flex flex-wrap gap-2 mt-3">
                  {receiptPath ? (
                    <span className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                      Receipt: <span className="text-white/80 ml-1 break-all">{receiptPath}</span>
                    </span>
                  ) : null}
                  {editId ? (
                    <span className={[pillBase(), "border-white/10 bg-black/20 text-white/70"].join(" ")}>
                      edit_id: <span className="text-white/80 ml-1 break-all">{editId}</span>
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
