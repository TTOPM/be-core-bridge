"use client";

import React, { useState } from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { Card } from "@/components/common/Card";
import { CodeBlock } from "@/components/common/CodeBlock";
import { Button } from "@/components/common/Button";
import { Modal } from "@/components/common/Modal";

export function ReceiptViewer() {
  const active = useProjectStore((s) => s.activeVersion());
  const [open, setOpen] = useState(false);

  const receipt = {
    project_id: active?.project_id ?? "—",
    version_id: active?.version_id ?? "—",
    edit_type: active?.edit_type ?? "—",
    edit_id: active?.edit_id ?? "",
    receipt_path: active?.receipt ?? "",
    benchmark: active?.benchmark ?? null,
    meta: active?.meta ?? {}
  };

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">Receipt</div>
      <div className="text-xs text-white/60">
        Step 2 will load the real receipt JSON from FastAPI. This view is already wired for it.
      </div>

      <Card className="p-3">
        <Button onClick={() => setOpen(true)}>Open Receipt Viewer</Button>
      </Card>

      <Modal open={open} title="Receipt JSON" onClose={() => setOpen(false)}>
        <CodeBlock value={receipt} />
      </Modal>
    </div>
  );
}
