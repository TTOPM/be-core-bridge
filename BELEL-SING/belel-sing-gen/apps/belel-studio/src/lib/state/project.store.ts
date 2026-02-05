import { create } from "zustand";
import { prjId, verId } from "@/lib/utils/id";
import { nowUtcIso } from "@/lib/utils/time";

export type Benchmark = {
  score_10: number;
  passed: boolean;
  alignment_pending?: boolean;
  gate_failures?: Record<string, unknown>;
};

export type Version = {
  project_id: string;
  version_id: string;
  utc: string;
  title: string;
  wav_path?: string;
  mel_path?: string;
  wav_sidecar?: string;
  receipt?: string;
  edit_id?: string;
  edit_type?: string;
  benchmark?: Benchmark;
  meta?: Record<string, unknown>;
  committed?: boolean;
};

type ProjectState = {
  projectId: string | null;
  title: string;
  versions: Version[];
  activeVersionId: string | null;
  isPlaying: boolean;

  ensureProject: (title?: string) => string;
  setProject: (projectId: string, title: string) => void;

  appendVersion: (v: Omit<Version, "utc"> & { utc?: string }) => void;
  setActiveVersion: (versionId: string) => void;
  activeVersion: () => Version | null;

  commitActive: () => void;
  togglePlay: () => void;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  projectId: null,
  title: "Untitled",
  versions: [],
  activeVersionId: null,
  isPlaying: false,

  ensureProject: (t) => {
    const state = get();
    if (state.projectId) return state.projectId;
    const id = prjId();
    set({ projectId: id, title: t ?? "Untitled" });
    // seed v0 immediately (even before audio exists) so Studio route can be stable
    const v0: Version = {
      project_id: id,
      version_id: verId(0),
      utc: nowUtcIso(),
      title: t ?? "Untitled",
      benchmark: { score_10: 0, passed: false }
    };
    set({ versions: [v0], activeVersionId: v0.version_id });
    return id;
  },

  setProject: (projectId, title) => set({ projectId, title }),

  appendVersion: (v) => {
    const utc = v.utc ?? nowUtcIso();
    const full: Version = { ...v, utc };
    const next = [...get().versions, full];
    set({ versions: next, activeVersionId: full.version_id });
  },

  setActiveVersion: (versionId) => set({ activeVersionId: versionId }),

  activeVersion: () => {
    const { versions, activeVersionId } = get();
    if (!activeVersionId) return null;
    return versions.find((x) => x.version_id === activeVersionId) ?? null;
  },

  commitActive: () => {
    const { activeVersionId, versions } = get();
    if (!activeVersionId) return;
    const next = versions.map((v) =>
      v.version_id === activeVersionId ? { ...v, committed: true } : v
    );
    set({ versions: next });
  },

  togglePlay: () => set({ isPlaying: !get().isPlaying })
}));
