"use client";

import React from "react";
import { cn } from "@/lib/utils/format";

export function Card({
  className,
  children
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("rounded-lg border border-white/10 bg-black/20", className ?? "")}>
      {children}
    </div>
  );
}
