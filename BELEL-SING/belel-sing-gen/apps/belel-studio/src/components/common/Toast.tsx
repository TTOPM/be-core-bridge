"use client";

import React, { useEffect } from "react";
import { cn } from "@/lib/utils/format";

export function Toast({
  open,
  message,
  variant = "info",
  onClose
}: {
  open: boolean;
  message: string;
  variant?: "info" | "success" | "danger";
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => onClose(), 2600);
    return () => clearTimeout(t);
  }, [open, onClose]);

  if (!open) return null;

  const v =
    variant === "success"
      ? "border-emerald-400/30 bg-emerald-500/15"
      : variant === "danger"
      ? "border-red-400/30 bg-red-500/15"
      : "border-white/10 bg-white/5";

  return (
    <div className={cn("fixed bottom-5 right-5 z-50 px-4 py-3 rounded border text-sm", v)}>
      <div className="text-white/90">{message}</div>
    </div>
  );
}
