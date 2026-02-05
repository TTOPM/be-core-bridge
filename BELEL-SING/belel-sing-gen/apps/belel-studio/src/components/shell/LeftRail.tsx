"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils/format";
import { useProjectStore } from "@/lib/state/project.store";

function NavItem({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(href + "/");
  return (
    <Link
      href={href}
      className={cn(
        "px-3 py-2 rounded-md text-sm block border border-transparent",
        active ? "bg-white/10 border-white/10" : "hover:bg-white/5"
      )}
    >
      {label}
    </Link>
  );
}

export function LeftRail() {
  const projectId = useProjectStore((s) => s.projectId);
  return (
    <aside className="h-screen border-r border-white/10 bg-black/25 p-4">
      <div className="mb-6">
        <div className="text-lg font-semibold tracking-wide">BELEL STUDIO</div>
        <div className="text-xs text-white/60">Protocol-first editing surface</div>
      </div>

      <div className="space-y-1">
        <NavItem href="/create" label="Create" />
        <NavItem href={projectId ? `/studio/${projectId}` : "/create"} label="Studio" />
        <NavItem href="/library" label="Library" />
        <NavItem href="/create" label="Exports" />
        <NavItem href="/create" label="Labs" />
        <NavItem href="/create" label="Settings" />
      </div>

      <div className="mt-8 p-3 rounded-md bg-white/5 border border-white/10">
        <div className="text-xs text-white/60">Active project</div>
        <div className="text-sm font-medium mt-1">{projectId ?? "None"}</div>
      </div>
    </aside>
  );
}
