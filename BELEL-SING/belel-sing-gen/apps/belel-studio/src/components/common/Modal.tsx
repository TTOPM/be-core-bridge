"use client";

import React, { useEffect } from "react";
import { cn } from "@/lib/utils/format";

export function Modal({
  open,
  title,
  children,
  onClose,
  className
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  className?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onMouseDown={onClose}
    >
      <div
        className={cn(
          "w-[980px] max-w-[95vw] rounded-lg border border-white/10 bg-[#0b0d12] shadow-xl",
          className ?? ""
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-white/10 flex items-center">
          <div className="font-semibold text-sm">{title}</div>
          <button className="ml-auto text-white/60 hover:text-white/90" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
