"use client";

import { create } from "zustand";

export type Benchmark = {
  score_10: number;
  passed: boolean;
  alignment_pending?: boolean | null;
  gate_failures?: Record<string, unknown> | null;
  breakdown?: Record<string, unknown> | null;
};

export type Version = {
  project_id: string;
  version_id: string;
  title: string;
  utc?: string;

  wav_path: string;
  mel_path: string;
  wav_sidecar: string;
  receipt?: string;

  edit_id?: string;
  edit_type?: string;

  benchmark?: Benchmark | null;
  meta?: Record<string, unknown>;
  committed?: boolean;
};

type ProjectState = {
  projectId: string | null;
  title: string;
  versions: Version[];
  activeVersionId: string | null;

  setProject: (projectId: string, title: string) => void;
  loadFromApi: (projectId: string) => Promise<void>;

  initFromGenerate: (v: Version) => void;
  appendVersion: (v: Version) => void;
  setActiveVersion: (versionId: string) => void;

  activeVersion: () => Version | null;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  projectId: null,
  title: "Untitled",
  versions: [],
  activeVersionId: null,

  setProject: (projectId, title) =>
    set({ projectId, title: title || "Untitled" }),

  loadFromApi: async (projectId: string) => {
    const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
      cache: "no-store",
    });
    const data = await res.json();
    const title = data?.title ?? "Untitled";
    const versions: Version[] = (data?.versions ?? []).map((v: any) => ({
      project_id: v.project_id ?? projectId,
      version_id: v.version_id,
      title,
      utc: v.utc,
      wav_path: v.wav_path,
      mel_path: v.mel_path,
      wav_sidecar: v.wav_sidecar,
      receipt: v.receipt ?? undefined,
      edit_id: v.edit_id ?? undefined,
      edit_type: v.edit_type ?? undefined,
      benchmark: v.benchmark ?? undefined,
      meta: v.meta ?? {},
      committed: Boolean(v.committed),
    }));

    set({
      projectId,
      title,
      versions,
      activeVersionId: data?.active_version_id ?? (versions[versions.length - 1]?.version_id ?? null),
    });
  },

  initFromGenerate: (v) =>
    set({
      projectId: v.project_id,
      title: v.title || "Untitled",
      versions: [v],
      activeVersionId: v.version_id,
    }),

  appendVersion: (v) =>
    set((s) => ({
      versions: [...s.versions, v],
      activeVersionId: v.version_id,
    })),

  setActiveVersion: (versionId) => set({ activeVersionId: versionId }),

  activeVersion: () => {
    const s = get();
    if (!s.activeVersionId) return null;
    return s.versions.find((v) => v.version_id === s.activeVersionId) ?? null;
  },
}));
