import { create } from "zustand";
import { clamp } from "@/lib/utils/format";

type SelectionState = {
  startSec: number;
  endSec: number;
  isLooping: boolean;
  setSelection: (a: number, b: number) => void;
  nudge: (deltaSec: number) => void;
  toggleLoop: () => void;
};

export const useSelectionStore = create<SelectionState>((set, get) => ({
  startSec: 0,
  endSec: 5,
  isLooping: false,
  setSelection: (a, b) => {
    const aa = clamp(a, 0, 1e9);
    const bb = clamp(b, 0, 1e9);
    const start = Math.min(aa, bb);
    const end = Math.max(aa, bb);
    set({ startSec: start, endSec: end });
  },
  nudge: (deltaSec) => {
    const { startSec, endSec } = get();
    const len = Math.max(0.01, endSec - startSec);
    const a = startSec + deltaSec;
    set({ startSec: Math.max(0, a), endSec: Math.max(0, a) + len });
  },
  toggleLoop: () => set({ isLooping: !get().isLooping })
}));
