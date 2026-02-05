"use client";

import React from "react";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common/Card";

export function GenerateButton({
  disabled,
  onCreate
}: {
  disabled: boolean;
  onCreate: () => void;
}) {
  return (
    <Card className="p-3">
      <div className="text-xs text-white/60 mb-2">Actions</div>
      <Button
        disabled={disabled}
        onClick={onCreate}
        className="w-full disabled:opacity-40 disabled:hover:bg-white/10"
      >
        Create → Studio
      </Button>
      <div className="text-xs text-white/50 mt-2">
        Step 1 sets up the Studio frame. Generation/edit endpoints are wired in Step 2.
      </div>
    </Card>
  );
}
