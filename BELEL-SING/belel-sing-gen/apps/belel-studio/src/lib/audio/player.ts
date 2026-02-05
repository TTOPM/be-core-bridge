"use client";

type PlayerState = {
  ctx: AudioContext | null;
  buffer: AudioBuffer | null;
  source: AudioBufferSourceNode | null;
  gain: GainNode | null;

  startedAt: number;  // ctx.currentTime when playback started
  offsetSec: number;  // buffer offset used at start
  playing: boolean;

  loop: boolean;
  loopStart: number;
  loopEnd: number;
};

const S: PlayerState = {
  ctx: null,
  buffer: null,
  source: null,
  gain: null,
  startedAt: 0,
  offsetSec: 0,
  playing: false,
  loop: false,
  loopStart: 0,
  loopEnd: 0,
};

function ensureCtx() {
  if (!S.ctx) S.ctx = new AudioContext();
  if (!S.gain && S.ctx) {
    S.gain = S.ctx.createGain();
    S.gain.gain.value = 1.0;
    S.gain.connect(S.ctx.destination);
  }
  return S.ctx!;
}

function stopSource() {
  try {
    S.source?.stop();
  } catch {}
  try {
    S.source?.disconnect();
  } catch {}
  S.source = null;
  S.playing = false;
}

export async function playerSetBuffer(buf: AudioBuffer) {
  ensureCtx();
  stopSource();
  S.buffer = buf;
  S.offsetSec = 0;
}

export function playerIsPlaying() {
  return S.playing;
}

export function playerDuration() {
  return S.buffer?.duration ?? 0;
}

export function playerCurrentTimeSec() {
  if (!S.ctx) return 0;
  if (!S.playing) return S.offsetSec;
  return (S.ctx.currentTime - S.startedAt) + S.offsetSec;
}

export function playerSetLoop(loop: boolean, startSec?: number, endSec?: number) {
  S.loop = Boolean(loop);
  if (typeof startSec === "number") S.loopStart = Math.max(0, startSec);
  if (typeof endSec === "number") S.loopEnd = Math.max(0, endSec);
}

export function playerSeek(sec: number) {
  const d = playerDuration();
  const t = Math.max(0, Math.min(d, sec));
  S.offsetSec = t;

  if (S.playing) {
    // restart at new offset
    playerPlay();
  }
}

export async function playerPlay() {
  const ctx = ensureCtx();
  if (!S.buffer || !S.gain) return;

  stopSource();

  const src = ctx.createBufferSource();
  src.buffer = S.buffer;
  src.connect(S.gain);

  // loop
  if (S.loop && S.loopEnd > S.loopStart) {
    src.loop = true;
    src.loopStart = S.loopStart;
    src.loopEnd = S.loopEnd;
  } else {
    src.loop = false;
  }

  S.source = src;
  S.startedAt = ctx.currentTime;
  S.playing = true;

  // start from offset
  src.start(0, S.offsetSec);

  src.onended = () => {
    // If loop was disabled mid-run, onended can fire
    if (S.source === src) {
      S.playing = false;
      S.source = null;
    }
  };
}

export function playerPause() {
  // WebAudio has no pause; stop + keep offset
  const t = playerCurrentTimeSec();
  stopSource();
  S.offsetSec = t;
}

export function playerSetGain(v: number) {
  if (!S.gain) ensureCtx();
  if (!S.gain) return;
  S.gain.gain.value = Math.max(0, Math.min(2.0, v));
}
