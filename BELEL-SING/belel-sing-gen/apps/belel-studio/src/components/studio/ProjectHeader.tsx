"use client";

import React from "react";
import { Card } from "@/components/common/Card";
import { useProjectStore } from "@/lib/state/project.store";
import { BenchmarkBadge } from "@/components/studio/BenchmarkBadge";
import { Button } from "@/components/common/Button";

export function ProjectHeader() {
  const title = useProjectStore((s) => s.title);
  const projectId = useProjectStore((s) => s.projectId);
  const active = useProjectStore((s) => s.activeVersion());

  return (
    <div className="p-4 border-b border-white/10 bg-black/20">
      <div className="flex items-center gap-3">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="text-xs text-white/60">
            Project: <span className="text-white/80">{projectId ?? "—"}</span>
            {" · "}
            Active: <span className="text-white/80">{active?.version_id ?? "—"}</span>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <BenchmarkBadge benchmark={active?.benchmark} />
          <Button
            onClick={() =>
              useProjectStore.getState().appendVersion({
                project_id: projectId ?? "unknown",
                version_id: `v${useProjectStore.getState().versions.length}`,
                title,
                benchmark: { score_10: 0, passed: false },
                edit_type: "manual_snapshot"
              })
            }
          >
            Snapshot
          </Button>
        </div>
      </div>

      <Card className="mt-3 p-3">
        <div className="text-xs text-white/60">
          This Studio frame is the exact surface we’ll wire to `/generate` and `/edit` next.
          Right panel will show receipts + benchmark gates + retries once the backend is connected.
        </div>
      </Card>
    </div>
  );
}
