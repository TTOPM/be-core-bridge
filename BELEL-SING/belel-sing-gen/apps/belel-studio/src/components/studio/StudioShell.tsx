"use client";

import React, { useEffect, useState } from "react";
import { ProjectHeader } from "@/components/studio/ProjectHeader";
import { ToolBar } from "@/components/studio/ToolBar";
import { InspectorPanel } from "@/components/studio/InspectorPanel";
import { RunHistoryList } from "@/components/studio/RunHistoryList";
import { ReceiptViewer } from "@/components/studio/ReceiptViewer";
import { PerformanceDrawer } from "@/components/studio/PerformanceDrawer";
import { WaveformTimeline } from "@/components/timeline/WaveformTimeline";
import { MelToggleView } from "@/components/timeline/MelToggleView";
import { Tabs } from "@/components/common/Tabs";
import { useProjectStore } from "@/lib/state/project.store";

export function StudioShell({ projectId }: { projectId: string }) {
  const setProject = useProjectStore((s) => s.setProject);
  const ensureProject = useProjectStore((s) => s.ensureProject);
  const [rightTab, setRightTab] = useState("Inspector");

  useEffect(() => {
    // Ensure store knows current projectId
    if (!projectId) return;
    setProject(projectId, useProjectStore.getState().title);
    // ensure baseline versions exist
    ensureProject(useProjectStore.getState().title);
  }, [projectId, setProject, ensureProject]);

  return (
    <div className="h-[calc(100vh-56px-64px)]">
      <div className="h-full grid grid-rows-[auto_1fr]">
        <ProjectHeader />

        <div className="h-full grid grid-cols-[1fr_420px]">
          {/* Center */}
          <div className="h-full border-r border-white/10">
            <div className="px-4 pt-4">
              <ToolBar />
            </div>

            <div className="px-4 mt-3">
              <WaveformTimeline />
            </div>

            <div className="px-4 mt-3 pb-6">
              <MelToggleView />
            </div>
          </div>

          {/* Right inspector */}
          <div className="h-full">
            <div className="p-4 border-b border-white/10">
              <Tabs
                tabs={["Inspector", "History", "Receipt", "Performance"]}
                active={rightTab}
                onChange={setRightTab}
              />
            </div>

            <div className="p-4 overflow-auto h-[calc(100%-56px)]">
              {rightTab === "Inspector" ? <InspectorPanel /> : null}
              {rightTab === "History" ? <RunHistoryList /> : null}
              {rightTab === "Receipt" ? <ReceiptViewer /> : null}
              {rightTab === "Performance" ? <PerformanceDrawer /> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
