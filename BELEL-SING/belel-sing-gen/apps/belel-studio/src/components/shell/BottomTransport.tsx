"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { useSelectionStore } from "@/lib/state/selection.store";
import { API } from "@/lib/api/routes";
import { Button } from "@/components/common/Button";
import { fmt2 } from "@/lib/utils/format";

export function BottomTransport() {
  const active = useProjectStore((s) => s.activeVersion());
  const selStart = useSelectionStore((s) => s.startSec);
  const selEnd = useSelectionStore((s) => s.endSec);
  const loop = useSelectionStore((s) => s.loop);
  const setLoop = useSelectionStore((s) => s.setLoop);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0);

  const wavUrl = useMemo(() => {
    if (!active?.wav_path) return null;
    return API.artifacts(active.wav_path);
  }, [active?.wav_path]);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;

    const onTime = () => setT(a.currentTime);
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);

    a.addEventListener("timeupdate", onTime);
    a.addEventListener("play", onPlay);
    a.addEventListener("pause", onPause);

    return () => {
      a.removeEventListener("timeupdate", onTime);
      a.removeEventListener("play", onPlay);
      a.removeEventListener("pause", onPause);
    };
  }, []);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;

    // Loop enforcement (simple + reliable)
    const id = window.setInterval(() => {
      if (!loop) return;
      if (!a.duration || !Number.isFinite(a.duration)) return;

      const start = Math.max(0, Math.min(selStart, a.duration));
      const end = Math.max(0, Math.min(selEnd, a.duration));
      if (end <= start) return;

      if (a.currentTime >= end) {
        a.currentTime = start;
        if (a.paused) a.play().catch(() => {});
      }
    }, 120);

    return () => window.clearInterval(id);
  }, [loop, selStart, selEnd]);

  function togglePlay() {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => {});
    else a.pause();
  }

  function jumpToSelection() {
    const a = audioRef.current;
    if (!a || !a.duration) return;
    a.currentTime = Math.max(0, Math.min(selStart, a.duration));
  }

  return (
    <div className="fixed left-0 right-0 bottom-0 border-t border-white/10 bg-black/80 backdrop-blur p-3 z-50">
      <div className="max-w-6xl mx-auto flex items-center gap-3">
        <audio ref={audioRef} src={wavUrl ?? undefined} preload="auto" />

        <Button disabled={!wavUrl} onClick={togglePlay}>
          {playing ? "Pause" : "Play"}
        </Button>

        <Button disabled={!wavUrl} onClick={jumpToSelection}>
          To Region
        </Button>

        <label className="flex items-center gap-2 text-xs text-white/70">
          <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} />
          Loop Region
        </label>

        <div className="flex-1" />

        <div className="text-xs text-white/60">
          {wavUrl ? `t=${fmt2(t)}s` : "No audio loaded"}
        </div>
      </div>
    </div>
  );
}
