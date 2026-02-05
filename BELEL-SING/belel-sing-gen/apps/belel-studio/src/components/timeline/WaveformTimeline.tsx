"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useProjectStore } from "@/lib/state/project.store";
import { useSelectionStore } from "@/lib/state/selection.store";
import { API } from "@/lib/api/routes";
import { fmt2 } from "@/lib/utils/format";

type WaveData = {
  duration: number;
  peaks: Float32Array; // normalized 0..1
};

async function decodeWavToPeaks(url: string, bins: number = 2000): Promise<WaveData> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`wave fetch failed: ${res.status}`);
  const buf = await res.arrayBuffer();

  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const audio = await ctx.decodeAudioData(buf.slice(0));

  const ch0 = audio.getChannelData(0);
  const len = ch0.length;
  const step = Math.max(1, Math.floor(len / bins));

  const peaks = new Float32Array(bins);
  for (let i = 0; i < bins; i++) {
    const start = i * step;
    const end = Math.min(len, start + step);
    let m = 0;
    for (let j = start; j < end; j++) {
      const v = Math.abs(ch0[j]);
      if (v > m) m = v;
    }
    peaks[i] = m;
  }

  // normalize
  let max = 0;
  for (let i = 0; i < peaks.length; i++) max = Math.max(max, peaks[i]);
  if (max > 0) {
    for (let i = 0; i < peaks.length; i++) peaks[i] = peaks[i] / max;
  }

  ctx.close().catch(() => {});
  return { duration: audio.duration, peaks };
}

export function WaveformTimeline() {
  const active = useProjectStore((s) => s.activeVersion());
  const setSelection = useSelectionStore((s) => s.setSelection);
  const selStart = useSelectionStore((s) => s.startSec);
  const selEnd = useSelectionStore((s) => s.endSec);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [wave, setWave] = useState<WaveData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const wavUrl = useMemo(() => {
    if (!active?.wav_path) return null;
    return API.artifacts(active.wav_path);
  }, [active?.wav_path]);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    setWave(null);

    if (!wavUrl) return;

    decodeWavToPeaks(wavUrl)
      .then((w) => {
        if (cancelled) return;
        setWave(w);
        // clamp selection into duration on first load
        const a = Math.max(0, Math.min(selStart, w.duration));
        const b = Math.max(0, Math.min(selEnd, w.duration));
        if (b <= a) setSelection(0, Math.min(5, w.duration));
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(e?.message ?? "wave decode failed");
      });

    return () => {
      cancelled = true;
    };
  }, [wavUrl]);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c || !wave) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = c.clientWidth;
    const height = c.clientHeight;

    c.width = Math.floor(width * dpr);
    c.height = Math.floor(height * dpr);
    ctx.scale(dpr, dpr);

    // background
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "rgba(255,255,255,0.04)";
    ctx.fillRect(0, 0, width, height);

    // waveform
    const mid = height / 2;
    ctx.strokeStyle = "rgba(255,255,255,0.75)";
    ctx.lineWidth = 1;

    const peaks = wave.peaks;
    const n = peaks.length;
    const stepX = width / n;

    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = i * stepX;
      const amp = peaks[i] * (height * 0.45);
      ctx.moveTo(x, mid - amp);
      ctx.lineTo(x, mid + amp);
    }
    ctx.stroke();

    // selection overlay
    const a = Math.max(0, Math.min(selStart, wave.duration));
    const b = Math.max(0, Math.min(selEnd, wave.duration));
    const x1 = (a / wave.duration) * width;
    const x2 = (b / wave.duration) * width;

    ctx.fillStyle = "rgba(120, 200, 255, 0.18)";
    ctx.fillRect(x1, 0, Math.max(1, x2 - x1), height);

    ctx.strokeStyle = "rgba(120, 200, 255, 0.8)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x1, 0);
    ctx.lineTo(x1, height);
    ctx.moveTo(x2, 0);
    ctx.lineTo(x2, height);
    ctx.stroke();
  }, [wave, selStart, selEnd]);

  function pointerToSec(e: React.PointerEvent, duration: number) {
    const rect = (e.currentTarget as HTMLCanvasElement).getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    return (x / rect.width) * duration;
  }

  const dragRef = useRef<{ dragging: boolean; anchor: number } | null>(null);

  function onPointerDown(e: React.PointerEvent) {
    if (!wave || !canvasRef.current) return;
    (e.currentTarget as HTMLCanvasElement).setPointerCapture(e.pointerId);
    const t = pointerToSec(e, wave.duration);
    dragRef.current = { dragging: true, anchor: t };
    setSelection(t, t);
  }

  function onPointerMove(e: React.PointerEvent) {
    const d = dragRef.current;
    if (!d?.dragging || !wave) return;
    const t = pointerToSec(e, wave.duration);
    setSelection(d.anchor, t);
  }

  function onPointerUp(e: React.PointerEvent) {
    const d = dragRef.current;
    if (!d || !wave) return;
    const t = pointerToSec(e, wave.duration);
    setSelection(d.anchor, t);
    dragRef.current = { dragging: false, anchor: d.anchor };
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-white/60">
        <div>
          {wave ? `Duration: ${fmt2(wave.duration)}s` : "Waveform: idle"}
        </div>
        <div>
          Region: {fmt2(selStart)}s → {fmt2(selEnd)}s
        </div>
      </div>

      {err ? <div className="text-xs text-red-200/80">{err}</div> : null}

      <div className="rounded border border-white/10 bg-black/30 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-[160px] block touch-none"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />
      </div>
    </div>
  );
}
