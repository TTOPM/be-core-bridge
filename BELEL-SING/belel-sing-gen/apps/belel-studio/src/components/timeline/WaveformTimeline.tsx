"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { useSelectionStore } from "@/lib/state/selection.store";
import { fetchArrayBuffer, decodeAudio, computePeaks, type Peaks } from "@/lib/audio/waveform";
import { playerSetBuffer, playerSeek, playerCurrentTimeSec, playerDuration } from "@/lib/audio/player";
import { RegionOverlay } from "@/components/timeline/RegionOverlay";
import { TimeRuler } from "@/components/timeline/TimeRuler";

function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

export function WaveformTimeline() {
  const active = useProjectStore((s) => s.activeVersion());
  const wavPath = active?.wav_path;

  const setSelection = useSelectionStore((s) => s.setSelection);
  const clearSelection = useSelectionStore((s) => s.clearSelection);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [peaks, setPeaks] = useState<Peaks | null>(null);
  const [loading, setLoading] = useState(false);
  const [cursorSec, setCursorSec] = useState(0);

  // load + decode
  useEffect(() => {
    let alive = true;

    async function run() {
      if (!wavPath) {
        setPeaks(null);
        return;
      }
      setLoading(true);
      try {
        const url = `/api/artifacts?path=${encodeURIComponent(wavPath)}`;
        const ab = await fetchArrayBuffer(url);

        const ctx = new AudioContext();
        const audio = await decodeAudio(ctx, ab);
        if (!alive) return;

        await playerSetBuffer(audio);

        const bins = 1800; // stable + smooth
        const p = computePeaks(audio, bins);
        setPeaks(p);
      } catch (e) {
        console.error(e);
        setPeaks(null);
      } finally {
        if (alive) setLoading(false);
      }
    }

    run();
    return () => {
      alive = false;
    };
  }, [wavPath]);

  // render waveform
  useEffect(() => {
    const c = canvasRef.current;
    const wrap = containerRef.current;
    if (!c || !wrap) return;

    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, wrap.clientWidth);
    const h = 120;

    c.width = Math.floor(w * dpr);
    c.height = Math.floor(h * dpr);
    c.style.width = `${w}px`;
    c.style.height = `${h}px`;

    const g = c.getContext("2d");
    if (!g) return;
    g.scale(dpr, dpr);

    // background
    g.clearRect(0, 0, w, h);
    g.fillStyle = "rgba(0,0,0,0.25)";
    g.fillRect(0, 0, w, h);

    // mid line
    g.strokeStyle = "rgba(255,255,255,0.08)";
    g.beginPath();
    g.moveTo(0, h / 2);
    g.lineTo(w, h / 2);
    g.stroke();

    if (!peaks) return;

    const bins = peaks.min.length;
    const step = w / bins;
    const mid = h / 2;

    g.strokeStyle = "rgba(255,255,255,0.55)";
    g.lineWidth = 1;

    for (let i = 0; i < bins; i++) {
      const x = i * step;
      const lo = peaks.min[i];
      const hi = peaks.max[i];
      const y1 = mid - hi * (h * 0.42);
      const y2 = mid - lo * (h * 0.42);

      g.beginPath();
      g.moveTo(x, y1);
      g.lineTo(x, y2);
      g.stroke();
    }
  }, [peaks]);

  // animate cursor
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const t = playerCurrentTimeSec();
      setCursorSec(t);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const durationSec = peaks?.durationSec ?? 0;

  const cursorLeftPx = useMemo(() => {
    const el = containerRef.current;
    if (!el) return 0;
    const w = el.clientWidth || 1;
    const d = Math.max(0.0001, durationSec || 0.0001);
    return clamp((cursorSec / d) * w, 0, w);
  }, [cursorSec, durationSec]);

  const onPointerDown = (e: React.PointerEvent) => {
    const el = containerRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const x0 = clamp(e.clientX - rect.left, 0, rect.width);
    const d = Math.max(0.0001, durationSec || 0.0001);
    const a0 = (x0 / rect.width) * d;

    // click without drag: seek
    let moved = false;

    const onMove = (ev: PointerEvent) => {
      moved = true;
      const x1 = clamp(ev.clientX - rect.left, 0, rect.width);
      const b0 = (x1 / rect.width) * d;
      setSelection(a0, b0);
    };

    const onUp = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);

      const x1 = clamp(ev.clientX - rect.left, 0, rect.width);
      const t = (x1 / rect.width) * d;

      if (!moved) {
        clearSelection();
        playerSeek(t);
      }
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] text-white/60">
          {loading ? "Loading waveform…" : peaks ? `Duration: ${durationSec.toFixed(2)}s` : "No audio loaded"}
        </div>
        <div className="text-[11px] text-white/50">
          Tip: drag to select • click to seek • double-click selection to clear
        </div>
      </div>

      <TimeRuler durationSec={durationSec} width={containerRef.current?.clientWidth ?? 900} />

      <div
        ref={containerRef}
        className="relative w-full rounded border border-white/10 bg-black/30 overflow-hidden"
        style={{ height: 120 }}
        onPointerDown={onPointerDown}
      >
        <canvas ref={canvasRef} />

        {/* selection overlay */}
        <RegionOverlay durationSec={durationSec} containerRef={containerRef} />

        {/* playhead */}
        <div
          className="absolute top-0 bottom-0 w-px bg-cyan-400/70"
          style={{ left: cursorLeftPx }}
          title="Playhead"
        />
      </div>
    </div>
  );
}
