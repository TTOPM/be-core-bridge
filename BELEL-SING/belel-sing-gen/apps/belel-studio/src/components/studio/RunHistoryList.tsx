"use client";

import React from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { Card } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { BenchmarkBadge } from "@/components/studio/BenchmarkBadge";

export function RunHistoryList() {
  const versions = useProjectStore((s) => s.versions);
  const setActive = useProjectStore((s) => s.setActiveVersion);

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">Run history</div>
      <div className="text-xs text-white/60">Every run becomes a version. Step 2 will attach receipt + artifacts.</div>

      <div className="space-y-2">
        {versions
          .slice()
          .reverse()
          .map((v) => (
            <Card key={v.version_id} className="p-3">
              <div className="flex items-center gap-2">
                <div className="text-sm font-medium">{v.version_id}</div>
                <div className="text-xs text-white/60">{v.edit_type ?? "source"}</div>
                <div className="ml-auto">
                  <BenchmarkBadge benchmark={v.benchmark} />
                </div>
              </div>
              <div className="text-xs text-white/50 mt-1">{v.utc}</div>
              <div className="mt-2">
                <Button onClick={() => setActive(v.version_id)}>Set Active</Button>
              </div>
            </Card>
          ))}
      </div>
    </div>
  );
}
