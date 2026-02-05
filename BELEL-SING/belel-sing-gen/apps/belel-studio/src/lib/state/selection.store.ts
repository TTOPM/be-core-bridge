"use client";

import { create } from "zustand";

export type SnapMode = "none" | "0.05s" | "0.10s" | "0.25s" | "0.50s" | "1.00s";

type SelectionState = {
  startSec: number | null;
  endSec: number | null;
  isLooping: boolean;
  snap: SnapMode;

  setSelection: (startSec: number | null, endSec: number | null) => void;
  clearSelection: () => void;

  setLooping: (v: boolean) => void;
  toggleLooping: () => void;

  setSnap: (s: SnapMode) => void;

  // helpers
  normalized: () => { startSec: number | null; endSec: number | null; has: boolean };
};

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

function snapValue(sec: number, mode: SnapMode) {
  if (mode === "none") return sec;
  const step =
    mode === "0.05s" ? 0.05 :
    mode === "0.10s" ? 0.10 :
    mode === "0.25s" ? 0.25 :
    mode === "0.50s" ? 0.50 :
    1.00;
  return Math.round(sec / step) * step;
}

export const useSelectionStore = create<SelectionState>((set, get) => ({
  startSec: null,
  endSec: null,
  isLooping: false,
  snap: "0.10s",

  setSelection: (a, b) => {
    if (a == null || b == null) {
      set({ startSec: null, endSec: null });
      return;
    }
    const s = get().snap;
    const aa = snapValue(a, s);
    const bb = snapValue(b, s);

    // normalize order
    const startSec = Math.min(aa, bb);
    const endSec = Math.max(aa, bb);

    // ignore tiny accidental selections
    if (endSec - startSec < 0.02) {
      set({ startSec: null, endSec: null });
      return;
    }
    set({ startSec, endSec });
  },

  clearSelection: () => set({ startSec: null, endSec: null }),

  setLooping: (v) => set({ isLooping: Boolean(v) }),
  toggleLooping: () => set({ isLooping: !get().isLooping }),

  setSnap: (snap) => set({ snap }),

  normalized: () => {
    const a = get().startSec;
    const b = get().endSec;
    if (a == null || b == null) return { startSec: null, endSec: null, has: false };
    const startSec = Math.min(a, b);
    const endSec = Math.max(a, b);
    return { startSec, endSec, has: endSec > startSec };
  },
}));
