import React from "react";
import { StudioShell } from "@/components/studio/StudioShell";

export default function StudioPage({ params }: { params: { projectId: string } }) {
  return <StudioShell projectId={params.projectId} />;
}