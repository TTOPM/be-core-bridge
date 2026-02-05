"use client";

import React from "react";
import { cn } from "@/lib/utils/format";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded bg-white/5 border border-white/10", className ?? "")} />
  );
}
