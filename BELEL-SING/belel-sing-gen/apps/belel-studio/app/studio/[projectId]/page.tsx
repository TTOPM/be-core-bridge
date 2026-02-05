"use client";

import React, { useEffect } from "react";
import { StudioShell } from "@/components/studio/StudioShell";
import { useProjectStore } from "@/lib/state/project.store";

export default function StudioPage({ params }: { params: { projectId: string } }) {
  const projectId = decodeURIComponent(params.projectId);
  const storeProjectId = useProjectStore((s) => s.projectId);
  const loadFromApi = useProjectStore((s) => s.loadFromApi);

  useEffect(() => {
    // Refresh-resilience: if store not loaded (hard refresh), load from backend index
    if (storeProjectId !== projectId) {
      loadFromApi(projectId).catch(() => {});
    }
  }, [projectId, storeProjectId, loadFromApi]);

  return <StudioShell />;
}
