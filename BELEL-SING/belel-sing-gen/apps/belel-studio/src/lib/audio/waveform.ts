"use client";

export type Peaks = {
  sampleRate: number;
  durationSec: number;
  // normalized peaks in [-1..1], length = bins
  min: Float32Array;
  max: Float32Array;
};

export async function fetchArrayBuffer(url: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch audio: ${res.status}`);
  return await res.arrayBuffer();
}

export async function decodeAudio(ctx: AudioContext, buf: ArrayBuffer) {
  // Safari needs copy
  const copy = buf.slice(0);
  return await ctx.decodeAudioData(copy);
}

export function computePeaks(audio: AudioBuffer, bins: number): Peaks {
  const ch = audio.numberOfChannels > 0 ? audio.getChannelData(0) : new Float32Array(0);
  const total = ch.length;
  const durationSec = audio.duration || 0;

  const min = new Float32Array(bins);
  const max = new Float32Array(bins);

  if (!total || !bins) {
    return { sampleRate: audio.sampleRate, durationSec, min, max };
  }

  const stride = Math.max(1, Math.floor(total / bins));

  for (let i = 0; i < bins; i++) {
    const start = i * stride;
    const end = Math.min(total, start + stride);
    let lo = 1.0;
    let hi = -1.0;
    for (let j = start; j < end; j++) {
      const v = ch[j];
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    min[i] = lo;
    max[i] = hi;
  }

  return { sampleRate: audio.sampleRate, durationSec, min, max };
}
