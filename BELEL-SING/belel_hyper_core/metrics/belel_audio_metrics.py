from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
import math

import numpy as np


@dataclass
class BelelAudioMetrics:
    sr: int
    n_samples: int
    duration_sec: float

    # safety / quality heuristics
    peak: float
    rms: float
    clip_frac: float
    dc_offset: float

    # spectral proxies (cheap, local)
    spec_centroid_hz: float
    spec_flatness: float

    # continuity proxies
    zcr: float  # zero-crossing rate
    energy_stability: float  # 1.0 = stable, 0.0 = very unstable

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_mono(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return x
    # [C,N] or [N,C]
    if x.shape[0] <= 8 and x.shape[0] < x.shape[-1]:
        return x.mean(axis=0)
    return x.mean(axis=-1)


def _frame(x: np.ndarray, frame: int, hop: int) -> np.ndarray:
    if len(x) < frame:
        pad = np.zeros(frame - len(x), dtype=x.dtype)
        x = np.concatenate([x, pad], axis=0)
    n = 1 + (len(x) - frame) // hop
    if n <= 0:
        n = 1
    out = np.zeros((n, frame), dtype=x.dtype)
    for i in range(n):
        s = i * hop
        out[i] = x[s : s + frame]
    return out


def _hann(n: int) -> np.ndarray:
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / max(1, n - 1))


def _stft_mag(x: np.ndarray, n_fft: int = 1024, hop: int = 256) -> Tuple[np.ndarray, np.ndarray]:
    frames = _frame(x, n_fft, hop) * _hann(n_fft)[None, :]
    # rfft
    spec = np.fft.rfft(frames, n=n_fft, axis=-1)
    mag = np.abs(spec).astype(np.float64) + 1e-12
    freqs = np.fft.rfftfreq(n_fft, d=1.0)  # normalized (Hz scaling applied outside)
    return mag, freqs


def compute_belel_audio_metrics(
    wav: np.ndarray,
    sr: int,
    *,
    n_fft: int = 1024,
    hop: int = 256,
    clip_thr: float = 0.999,
) -> BelelAudioMetrics:
    """
    Pure-local metrics; no web; no model calls.
    Designed to be fast and stable enough for evolution ranking.
    """
    x = np.asarray(wav, dtype=np.float32)
    x = _to_mono(x)

    n = int(x.shape[0])
    dur = float(n) / float(sr) if sr > 0 else 0.0

    peak = float(np.max(np.abs(x))) if n else 0.0
    rms = float(np.sqrt(np.mean(x * x))) if n else 0.0
    clip_frac = float(np.mean(np.abs(x) >= float(clip_thr))) if n else 0.0
    dc_offset = float(np.mean(x)) if n else 0.0

    # ZCR
    if n > 1:
        zc = np.mean((x[:-1] * x[1:]) < 0.0)
    else:
        zc = 0.0
    zcr = float(zc)

    # STFT-based proxies
    mag, freqs_norm = _stft_mag(x, n_fft=n_fft, hop=hop)
    freqs_hz = freqs_norm * float(sr)

    # centroid: sum(f * mag) / sum(mag)
    mag_sum = np.sum(mag, axis=1) + 1e-12
    centroid = np.sum(mag * freqs_hz[None, :], axis=1) / mag_sum
    spec_centroid_hz = float(np.mean(centroid)) if centroid.size else 0.0

    # flatness: geometric mean / arithmetic mean
    geo = np.exp(np.mean(np.log(mag), axis=1))
    ari = np.mean(mag, axis=1) + 1e-12
    flat = geo / ari
    spec_flatness = float(np.mean(flat)) if flat.size else 0.0

    # energy stability: 1 - normalized std of frame RMS
    frame_rms = np.sqrt(np.mean((_frame(x, n_fft, hop) ** 2), axis=1) + 1e-12)
    mu = float(np.mean(frame_rms)) + 1e-12
    sigma = float(np.std(frame_rms))
    # stable if sigma small relative to mean
    rel = min(10.0, sigma / mu)
    energy_stability = float(max(0.0, 1.0 - (rel / 2.0)))  # maps ~0..2 -> 1..0

    return BelelAudioMetrics(
        sr=int(sr),
        n_samples=n,
        duration_sec=dur,
        peak=peak,
        rms=rms,
        clip_frac=clip_frac,
        dc_offset=dc_offset,
        spec_centroid_hz=spec_centroid_hz,
        spec_flatness=spec_flatness,
        zcr=zcr,
        energy_stability=energy_stability,
    )
