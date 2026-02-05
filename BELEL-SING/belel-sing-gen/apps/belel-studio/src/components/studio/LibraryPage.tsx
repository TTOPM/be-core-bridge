"use client";

import React from "react";
import { Card } from "@/components/common/Card";
import { useProjectStore } from "@/lib/state/project.store";
import { Button } from "@/components/common/Button";
import { useRouter } from "next/navigation";

export function LibraryPage() {
  const router = useRouter();
  const pid = useProjectStore((s) => s.projectId);
  const versions = useProjectStore((s) => s.versions);

  return (
    <div className="max-w-[1100px] space-y-4">
      <div>
        <div className="text-xl font-semibold">Library</div>
        <div className="text-sm text-white/60">
          Step 2 will load projects from FastAPI /api/projects (project_index.json).
        </div>
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Current in-memory project</div>
        <div className="text-xs text-white/60 mt-1">Project: {pid ?? "—"}</div>
        <div className="text-xs text-white/60">Versions: {versions.length}</div>

        <div className="mt-3">
          <Button onClick={() => (pid ? router.push(`/studio/${pid}`) : router.push("/create"))}>
            Open Studio
          </Button>
        </div>
      </Card>
    </div>
  );
}
