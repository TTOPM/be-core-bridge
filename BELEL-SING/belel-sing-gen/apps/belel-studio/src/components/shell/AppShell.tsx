"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { LeftRail } from "@/components/shell/LeftRail";
import { TopBar } from "@/components/shell/TopBar";
import { BottomTransport } from "@/components/shell/BottomTransport";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showTransport = pathname.startsWith("/studio/");

  return (
    <div className="h-screen w-screen grid grid-cols-[268px_1fr]">
      <LeftRail />
      <div className="h-screen flex flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto">{children}</main>
        {showTransport ? <BottomTransport /> : null}
      </div>
    </div>
  );
}
