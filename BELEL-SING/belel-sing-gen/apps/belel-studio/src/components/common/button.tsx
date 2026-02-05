"use client";

import React from "react";
import { cn } from "@/lib/utils/format";

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "ghost" | "danger";
  }
) {
  const { className, variant = "primary", ...rest } = props;

  const base = "px-3 py-2 rounded text-sm transition-colors border";
  const v =
    variant === "danger"
      ? "bg-red-500/15 hover:bg-red-500/25 border-red-400/25"
      : variant === "ghost"
      ? "bg-transparent hover:bg-white/5 border-transparent"
      : "bg-white/10 hover:bg-white/15 border-white/10";

  return <button {...rest} className={cn(base, v, className ?? "")} />;
}
