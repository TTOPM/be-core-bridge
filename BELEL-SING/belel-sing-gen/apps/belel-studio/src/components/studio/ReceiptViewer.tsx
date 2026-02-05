"use client";

import React, { useMemo, useState } from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { Card } from "@/components/common/Card";
import { CodeBlock } from "@/components/common/CodeBlock";
import { Button } from "@/components/common/Button";
import { Modal } from "@/components/common/Modal";
import { apiJson } from "@/lib/api/client";
import { z } from "zod";

const ReceiptSchema = z.object({ receipt: z.record(z.unknown()) });

export function ReceiptViewer() {
  const active = useProjectStore((s) => s.activeVersion());
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const canLoad = Boolean(active?.project_id && active?.version_id);

  const url = useMemo(() => {
    if (!active?.project_id || !active?.version_id) return null;
    return `/api/receipt/${encodeURIComponent(active.project_id)}/${encodeURIComponent(active.version_id)}`;
  }, [active?.project_id, active?.version_id]);

  async function load() {
    setErr(null);
    setData(null);
    try {
      if (!url) throw new Error("receipt url missing");
      const res = await apiJson(url, ReceiptSchema);
      setData(res.receipt);
    } catch (e: any) {
      setErr(e?.message ?? "receipt load failed");
    }
  }

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">Receipt</div>
      <div className="text-xs text-white/60">
        Loads the authoritative receipt JSON from FastAPI.
      </div>

      <Card className="p-3 flex gap-2">
        <Button disabled={!canLoad} onClick={() => { setOpen(true); load(); }}>
          Open Receipt Viewer
        </Button>
        {err ? <div className="text-xs text-red-200/80 mt-2">{err}</div> : null}
      </Card>

      <Modal open={open} title="Receipt JSON" onClose={() => setOpen(false)}>
        <CodeBlock value={data ?? { loading: true }} />
      </Modal>
    </div>
  );
}
