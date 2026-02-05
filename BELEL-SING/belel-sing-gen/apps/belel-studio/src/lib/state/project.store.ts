"use client";

import { create } from "zustand";

export type ProtocolBenchmark = {
  score_10: number;
  passed: boolean;
  breakdown?: any;
  alignment_pending?: boolean;
};

export type VersionRecord = {
  version_id: string;
  project_id: string;

  wav_path: string;
  mel_path: string;
  wav_sidecar?: string;
  receipt?: string;

  edit_id?: string;
  edit_type?: string;

  meta?: any;
  benchmark?: ProtocolBenchmark;
  utc?: string;
};

type ProjectState = {
  projectId: string | null;
  title: string | null;

  versions: VersionRecord[];
  activeVersionId: string | null;

  activeVersion: () => VersionRecord | null;

  setProject: (args: { projectId: string; title?: string | null }) => void;
  resetProject: () => void;

  setVersions: (versions: VersionRecord[]) => void;
  appendVersion: (v: VersionRecord) => void;

  setActiveVersion: (versionId: string) => void;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  projectId: null,
  title: null,

  versions: [],
  activeVersionId: null,

  activeVersion: () => {
    const id = get().activeVersionId;
    if (!id) return null;
    return get().versions.find((v) => v.version_id === id) ?? null;
  },

  setProject: ({ projectId, title }) => set({ projectId, title: title ?? null }),

  resetProject: () =>
    set({ projectId: null, title: null, versions: [], activeVersionId: null }),

  setVersions: (versions) => {
    const next = Array.isArray(versions) ? versions : [];
    const currentActive = get().activeVersionId;
    const stillExists =
      currentActive && next.some((v) => v.version_id === currentActive);

    set({
      versions: next,
      activeVersionId: stillExists
        ? currentActive
        : next.at(-1)?.version_id ?? null,
    });
  },

  appendVersion: (v) => {
    set({
      versions: [...get().versions, v],
      activeVersionId: v.version_id,
    });
  },

  setActiveVersion: (versionId) => {
    if (!get().versions.some((v) => v.version_id === versionId)) return;
    set({ activeVersionId: versionId });
  },
}));
