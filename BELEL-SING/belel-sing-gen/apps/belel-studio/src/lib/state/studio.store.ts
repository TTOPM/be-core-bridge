import { create } from "zustand";

export type EditTool = "repaint" | "extend" | "retake" | "lyric_edit";

type StudioState = {
  tool: EditTool;
  strength: number;
  fadeSec: number;
  stepsOverride: 2 | 4 | 6;
  guidanceOverride: number;
  extendSec: number;
  lyricsDraft: string;
  setTool: (t: EditTool) => void;
  setStrength: (v: number) => void;
  setFadeSec: (v: number) => void;
  setStepsOverride: (v: 2 | 4 | 6) => void;
  setGuidanceOverride: (v: number) => void;
  setExtendSec: (v: number) => void;
  setLyricsDraft: (v: string) => void;
};

export const useStudioStore = create<StudioState>((set) => ({
  tool: "repaint",
  strength: 0.85,
  fadeSec: 0.08,
  stepsOverride: 4,
  guidanceOverride: 6.0,
  extendSec: 15,
  lyricsDraft: "",
  setTool: (t) => set({ tool: t }),
  setStrength: (v) => set({ strength: v }),
  setFadeSec: (v) => set({ fadeSec: v }),
  setStepsOverride: (v) => set({ stepsOverride: v }),
  setGuidanceOverride: (v) => set({ guidanceOverride: v }),
  setExtendSec: (v) => set({ extendSec: v }),
  setLyricsDraft: (v) => set({ lyricsDraft: v })
}));
