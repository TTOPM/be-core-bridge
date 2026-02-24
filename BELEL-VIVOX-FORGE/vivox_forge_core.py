# BELEL-VIVOX FORGE v1.4.1 — Patched, Fortified, Adaptive High-Fidelity Vocal Organ
# - Real source–filter synthesis (LF glottal excitation -> time-varying resonator bank)
# - Singer's formant cluster implemented as clustered resonances (not additive sines)
# - Physically plausible jitter/shimmer (frame/cycle-level), living breath, vibrato, emotional contour
# - Hardware-adaptive performance parameters (SR/oversample/block sizes/resonance density)
# - No external network calls. No cloud dependencies.
#
# Usage:
#   python3 BELEL-VIVOX-FORGE/vivox_forge_core.py
#
# Output:
#   vivox_test_output.wav
#
# IMPORTANT:
#   Intelligible lyrics require a text->phoneme+prosody module; this is the vocal organ core.
#   Provide phoneme_sequence to control pronunciation.

from __future__ import annotations

import math
import os
import platform
import struct
import sys
import wave
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


# =========================
# 0) Device profiling
# =========================

@dataclass(frozen=True)
class DeviceProfile:
    cpu_cores_physical: int
    ram_gb: float
    machine: str
    is_apple_silicon: bool
    is_low_power: bool
    sr_out: int
    oversample: int
    block_size: int
    resonance_detail: str  # "lite" | "full"
    breath_quality: str    # "lite" | "full"


def _safe_int(x, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _detect_device_profile() -> DeviceProfile:
    machine = (platform.machine() or "").lower()
    is_apple_silicon = machine in ("arm64", "aarch64")

    # cores/ram
    if psutil is not None:
        cores_phys = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 4
        ram_gb = float(psutil.virtual_memory().total) / (1024.0 ** 3)
    else:
        cores_phys = os.cpu_count() or 4
        ram_gb = 8.0  # conservative fallback

    # Low-power heuristic:
    # - <=4 physical cores OR RAM < 12GB -> low power
    # - do NOT penalize x86 by default; only use resource-based heuristics
    is_low_power = (cores_phys <= 4) or (ram_gb < 12.0)

    # Adaptive performance defaults
    # We keep "quality intent" constant; only compute knobs scale.
    if is_low_power:
        sr_out = 48000
        oversample = 1
        block_size = 256
        resonance_detail = "lite"   # fewer/cheaper upper resonances
        breath_quality = "lite"
        banner = "🔧 Adaptive mode: low-power profile (clarity-first, stable CPU)"
    else:
        sr_out = 96000
        oversample = 1
        block_size = 256
        resonance_detail = "full"
        breath_quality = "full"
        banner = "🔧 Adaptive mode: high-performance profile (96 kHz, full resonance detail)"

    # Optional override: VIVOX_SR=192000 to force 192k output if you want it.
    env_sr = os.getenv("VIVOX_SR", "").strip()
    if env_sr:
        forced = _safe_int(env_sr, sr_out)
        if forced in (44100, 48000, 88200, 96000, 176400, 192000):
            sr_out = forced
            banner = f"🔧 Adaptive mode: forced SR via VIVOX_SR={sr_out}"

    print(banner)
    return DeviceProfile(
        cpu_cores_physical=int(cores_phys),
        ram_gb=float(ram_gb),
        machine=machine,
        is_apple_silicon=bool(is_apple_silicon),
        is_low_power=bool(is_low_power),
        sr_out=int(sr_out),
        oversample=int(oversample),
        block_size=int(block_size),
        resonance_detail=resonance_detail,
        breath_quality=breath_quality,
    )


# =========================
# 1) DSP primitives
# =========================

def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _soft_clip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    # smooth limiter; avoids harsh digital clipping
    y = np.tanh(x * drive)
    return y / (np.max(np.abs(y)) + 1e-12)


def _dc_block(x: np.ndarray, r: float = 0.995) -> np.ndarray:
    # simple DC blocker: y[n] = x[n] - x[n-1] + r*y[n-1]
    y = np.zeros_like(x)
    xm1 = 0.0
    ym1 = 0.0
    for i in range(x.size):
        xi = float(x[i])
        yi = xi - xm1 + r * ym1
        y[i] = yi
        xm1 = xi
        ym1 = yi
    return y


def _biquad_bandpass_coeffs(f0_hz: float, q: float, sr: int) -> Tuple[float, float, float, float, float]:
    # RBJ audio EQ cookbook — constant skirt gain, peak gain = Q
    # b0 =   alpha
    # b1 =   0
    # b2 =  -alpha
    # a0 =   1 + alpha
    # a1 =  -2*cos(w0)
    # a2 =   1 - alpha
    w0 = 2.0 * math.pi * max(1.0, min(f0_hz, 0.49 * sr)) / sr
    cw = math.cos(w0)
    sw = math.sin(w0)
    alpha = sw / (2.0 * max(0.05, q))
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * cw
    a2 = 1.0 - alpha
    # normalize by a0
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0
    return b0, b1, b2, a1, a2


@dataclass
class BiquadState:
    z1: float = 0.0
    z2: float = 0.0


def _biquad_process_block(x: np.ndarray, coeffs: Tuple[float, float, float, float, float], st: BiquadState) -> np.ndarray:
    b0, b1, b2, a1, a2 = coeffs
    y = np.empty_like(x)
    z1 = st.z1
    z2 = st.z2
    # Direct Form II Transposed
    for i in range(x.size):
        xi = float(x[i])
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    st.z1 = z1
    st.z2 = z2
    return y


# =========================
# 2) LF glottal excitation (flow-derivative-style pulse)
# =========================

@dataclass
class LFParams:
    # Normalized timing parameters relative to one period T0:
    # Tp: time of max flow derivative in opening phase
    # Te: end of open phase (negative peak in derivative)
    # Ta: return phase time constant (closing)
    tp: float = 0.40
    te: float = 0.55
    ta: float = 0.12
    # spectral tilt control (simple additional shaping)
    tilt_db_per_oct: float = 12.0


def _lf_pulse_derivative(phase: np.ndarray, p: LFParams) -> np.ndarray:
    """
    Generate one-period glottal flow derivative-like pulse over phase in [0,1).
    This is a stable, synthesis-focused LF-style pulse (not a full parameter-solver).
    """
    # Ensure monotonic ordering
    tp = float(np.clip(p.tp, 0.15, 0.85))
    te = float(np.clip(p.te, tp + 0.05, 0.95))
    ta = float(np.clip(p.ta, 0.02, 0.45))

    y = np.zeros_like(phase, dtype=np.float64)

    # Opening + closing (quasi-sinusoid squared) for stability
    # - Opening: 0..tp
    m1 = phase < tp
    ph1 = phase[m1] / max(tp, 1e-6)
    y[m1] = np.sin(np.pi * ph1) ** 2

    # - Closing: tp..te (cosine-squared)
    m2 = (phase >= tp) & (phase < te)
    ph2 = (phase[m2] - tp) / max(te - tp, 1e-6)
    y[m2] = np.cos(0.5 * np.pi * ph2) ** 2

    # Return: te..1 (exponential decay)
    m3 = phase >= te
    ph3 = (phase[m3] - te) / max(1.0 - te, 1e-6)
    y[m3] = 0.35 * np.exp(-ph3 / max(ta, 1e-6))

    # Center to near-zero mean (helps DC)
    y -= np.mean(y)
    # Normalize peak
    y /= (np.max(np.abs(y)) + 1e-12)
    return y.astype(np.float32)


def _excitation_from_f0(
    f0_hz: np.ndarray,
    sr: int,
    pressure_env: np.ndarray,
    lf: LFParams,
) -> np.ndarray:
    """
    Time-domain LF excitation with cycle-accurate phase accumulation.
    f0_hz: per-sample fundamental frequency contour
    pressure_env: per-sample amplitude/pressure envelope
    """
    n = f0_hz.size
    phase = np.zeros(n, dtype=np.float64)
    ph = 0.0
    for i in range(n):
        ph += float(f0_hz[i]) / sr
        ph -= math.floor(ph)
        phase[i] = ph

    pulse = _lf_pulse_derivative(phase, lf)

    # Simple spectral tilt: 1-pole lowpass as tilt proxy
    # More tilt => more smoothing.
    # This is compute-cheap and stable.
    tilt = float(np.clip(lf.tilt_db_per_oct, 0.0, 24.0))
    # map tilt to smoothing coefficient
    a = 0.0 if tilt <= 0.1 else float(np.clip(1.0 - (tilt / 24.0) * 0.25, 0.65, 0.98))
    y = np.empty_like(pulse)
    acc = 0.0
    for i in range(n):
        acc = a * acc + (1.0 - a) * float(pulse[i])
        y[i] = acc

    y = y * pressure_env
    return y.astype(np.float32)


# =========================
# 3) Formant / resonance model
# =========================

# Simple formant table (Hz) for vowels + a neutral fallback.
# You can extend this.
FORMANT_TABLE: Dict[str, Tuple[float, float, float, float]] = {
    "iy": (270, 2290, 3010, 3350),
    "ih": (390, 1990, 2550, 3200),
    "eh": (530, 1840, 2480, 3200),
    "ae": (660, 1720, 2410, 3100),
    "aa": (730, 1090, 2440, 3400),
    "ah": (700, 1220, 2600, 3500),
    "ao": (570, 840, 2410, 3300),
    "ow": (570, 840, 2410, 3300),
    "uh": (440, 1020, 2240, 3400),
    "uw": (300, 870, 2240, 3400),
    "er": (490, 1350, 1690, 2900),
    "neutral": (550, 1450, 2550, 3450),
}

# Singer's formant cluster: clustered resonances near 2.5–3.2 kHz.
SINGER_CLUSTER_HZ = (2550.0, 2850.0, 3150.0)


@dataclass
class ResonatorSpec:
    f_hz: float
    q: float
    gain: float
    state: BiquadState


def _make_resonator_bank(
    sr: int,
    f1: float, f2: float, f3: float, f4: float,
    detail: str,
) -> List[ResonatorSpec]:
    """
    Build a resonator bank for formants + singer cluster.
    detail="lite" uses fewer/cheaper upper resonances.
    """
    # Q values: formants moderate; singer cluster tighter.
    specs: List[ResonatorSpec] = [
        ResonatorSpec(f1, 7.0, 1.00, BiquadState()),
        ResonatorSpec(f2, 9.0, 0.85, BiquadState()),
        ResonatorSpec(f3, 11.0, 0.70, BiquadState()),
    ]
    if detail == "full":
        specs.append(ResonatorSpec(f4, 12.0, 0.55, BiquadState()))
        # singer cluster as multiple resonances
        specs.append(ResonatorSpec(SINGER_CLUSTER_HZ[0], 18.0, 0.55, BiquadState()))
        specs.append(ResonatorSpec(SINGER_CLUSTER_HZ[1], 22.0, 0.70, BiquadState()))
        specs.append(ResonatorSpec(SINGER_CLUSTER_HZ[2], 18.0, 0.55, BiquadState()))
    else:
        # lite: keep one ring resonance
        specs.append(ResonatorSpec(2950.0, 18.0, 0.65, BiquadState()))
    return specs


def _render_resonances_time_varying(
    x: np.ndarray,
    sr: int,
    bank: List[ResonatorSpec],
    f_targets: List[Tuple[float, float, float, float]],
    block_size: int,
) -> np.ndarray:
    """
    Process excitation through a time-varying resonator bank by updating
    coefficients once per block. f_targets: per-block target formants
    (f1,f2,f3,f4) in Hz for the vowel identity.
    """
    y = np.zeros_like(x, dtype=np.float32)
    n = x.size
    nb = (n + block_size - 1) // block_size

    # Precompute a gentle crossfade for coefficient transitions per block
    # (Coefficient zipper noise reduction by smooth block-to-block update)
    prev_coeffs: List[Tuple[float, float, float, float, float]] = []
    coeffs: List[Tuple[float, float, float, float, float]] = []

    for _ in bank:
        prev_coeffs.append(_biquad_bandpass_coeffs(500.0, 8.0, sr))
        coeffs.append(prev_coeffs[-1])

    for bi in range(nb):
        b0 = bi * block_size
        b1 = min((bi + 1) * block_size, n)
        xb = x[b0:b1]

        # determine target formants for this block
        f1t, f2t, f3t, f4t = f_targets[min(bi, len(f_targets) - 1)]

        # update resonator frequencies
        # Map targets into bank: first 4 resonators track F1..F4 where present
        # Singer cluster stays fixed.
        formant_targets = [f1t, f2t, f3t, f4t]
        for i, spec in enumerate(bank):
            if i < 4:
                ft = formant_targets[i]
                spec.f_hz = float(ft)

        # compute new coeffs per spec
        for i, spec in enumerate(bank):
            prev_coeffs[i] = coeffs[i]
            coeffs[i] = _biquad_bandpass_coeffs(spec.f_hz, spec.q, sr)

        # process block through each resonator, sum with gains
        # For stability, we process each resonator independently and sum.
        yb = np.zeros_like(xb, dtype=np.float32)
        for i, spec in enumerate(bank):
            # small coefficient interpolation across the block
            # to reduce zipper noise:
            # We'll linearly interpolate b0,b1,b2,a1,a2 across samples in the block.
            # This is slightly more CPU but still safe at our SR defaults.
            pc = prev_coeffs[i]
            nc = coeffs[i]
            if xb.size == 0:
                continue

            # If block is large, we can approximate with 2 sub-blocks for speed.
            # But default block_size=256 keeps this cheap and smooth.
            # We'll do full interpolation only when coefficients changed meaningfully.
            diff = sum(abs(nc[k] - pc[k]) for k in range(5))
            if diff < 1e-4:
                filt = _biquad_process_block(xb, nc, spec.state)
                yb += (filt * spec.gain).astype(np.float32)
            else:
                # interpolate coefficients samplewise
                st = spec.state
                z1 = st.z1
                z2 = st.z2
                out = np.empty_like(xb, dtype=np.float32)

                for s in range(xb.size):
                    t = 0.0 if xb.size == 1 else (s / (xb.size - 1))
                    b0i = pc[0] + (nc[0] - pc[0]) * t
                    b1i = pc[1] + (nc[1] - pc[1]) * t
                    b2i = pc[2] + (nc[2] - pc[2]) * t
                    a1i = pc[3] + (nc[3] - pc[3]) * t
                    a2i = pc[4] + (nc[4] - pc[4]) * t

                    xi = float(xb[s])
                    yi = b0i * xi + z1
                    z1 = b1i * xi - a1i * yi + z2
                    z2 = b2i * xi - a2i * yi
                    out[s] = yi

                st.z1 = z1
                st.z2 = z2
                yb += (out * spec.gain).astype(np.float32)

        y[b0:b1] = yb

    return y


# =========================
# 4) Breath / noise / consonant shaping
# =========================

def _pinkish_noise(n: int, sr: int, quality: str) -> np.ndarray:
    # Lightweight pink-ish noise via filtering white noise
    w = np.random.randn(n).astype(np.float32)
    if quality == "lite":
        # 1-pole lowpass cumulative for "pink-ish"
        y = np.empty_like(w)
        a = 0.995
        acc = 0.0
        for i in range(n):
            acc = a * acc + (1.0 - a) * float(w[i])
            y[i] = acc
        y /= (np.max(np.abs(y)) + 1e-12)
        return y

    # quality == "full": two-stage filtering for more breath realism
    y1 = np.empty_like(w)
    a1 = 0.992
    acc1 = 0.0
    for i in range(n):
        acc1 = a1 * acc1 + (1.0 - a1) * float(w[i])
        y1[i] = acc1

    y2 = np.empty_like(y1)
    a2 = 0.997
    acc2 = 0.0
    for i in range(n):
        acc2 = a2 * acc2 + (1.0 - a2) * float(y1[i])
        y2[i] = acc2

    y2 /= (np.max(np.abs(y2)) + 1e-12)
    return y2.astype(np.float32)


def _consonant_noise_mask(phoneme: str, seg_n: int) -> np.ndarray:
    # Simple onset burst masks for fricatives/plosives.
    # This is intentionally modest to avoid harshness.
    if phoneme in ("s", "sh", "f", "th", "h", "v", "z", "k", "t", "p", "ch"):
        m = np.zeros(seg_n, dtype=np.float32)
        onset = max(8, seg_n // 6)
        ramp = np.linspace(0.0, 1.0, onset, dtype=np.float32)
        m[:onset] = ramp
        m[onset: min(seg_n, onset * 2)] = 1.0
        # decay
        if seg_n > onset * 2:
            dec = np.linspace(1.0, 0.0, seg_n - onset * 2, dtype=np.float32) ** 2.0
            m[onset * 2:] = dec
        return m
    return np.zeros(seg_n, dtype=np.float32)


# =========================
# 5) Prosody: vibrato, jitter, shimmer, emotion
# =========================

@dataclass
class ProsodyParams:
    vibrato_hz: float = 5.8
    vibrato_depth_semitones: float = 0.25   # musical vibrato depth
    jitter_rel_std: float = 0.0035          # ~0.35% (frame-level)
    shimmer_rel_std: float = 0.012          # ~1.2% slow AM
    shimmer_rate_hz: float = 7.5
    emotional_rise: float = 1.22
    phrase_count: int = 10


def _semitones_to_ratio(st: float) -> float:
    return 2.0 ** (st / 12.0)


def _make_f0_contour(
    base_f0: float,
    n: int,
    sr: int,
    pros: ProsodyParams,
) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / float(sr)

    # Vibrato in semitone domain
    vib = np.sin(2.0 * np.pi * pros.vibrato_hz * t).astype(np.float32)
    vib_ratio = np.power(_semitones_to_ratio(pros.vibrato_depth_semitones), vib).astype(np.float32)

    # Frame-level jitter: random walk at ~100 Hz control rate
    ctrl_rate = 100
    ctrl_n = max(2, int((n / sr) * ctrl_rate))
    j = np.random.randn(ctrl_n).astype(np.float32) * float(pros.jitter_rel_std)
    # smooth jitter by cumulative lowpass
    a = 0.85
    acc = 0.0
    for i in range(ctrl_n):
        acc = a * acc + (1.0 - a) * float(j[i])
        j[i] = acc
    j = np.clip(j, -0.02, 0.02)

    # upsample jitter to sample-rate
    j_up = np.interp(np.linspace(0, ctrl_n - 1, n), np.arange(ctrl_n), j).astype(np.float32)

    f0 = float(base_f0) * vib_ratio * (1.0 + j_up)
    f0 = np.clip(f0, 60.0, 880.0).astype(np.float32)
    return f0


def _make_am_envelope(
    n: int,
    sr: int,
    pros: ProsodyParams,
) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / float(sr)

    # Slow shimmer AM (sin + smoothed noise)
    shimmer = np.sin(2.0 * np.pi * pros.shimmer_rate_hz * t).astype(np.float32)

    noise = np.random.randn(n).astype(np.float32)
    a = 0.999
    acc = 0.0
    for i in range(n):
        acc = a * acc + (1.0 - a) * float(noise[i])
        noise[i] = acc
    noise /= (np.max(np.abs(noise)) + 1e-12)

    am = 1.0 + float(pros.shimmer_rel_std) * (0.55 * shimmer + 0.45 * noise)
    am = np.clip(am, 0.85, 1.25).astype(np.float32)
    return am


def _apply_emotional_envelope(x: np.ndarray, sr: int, pros: ProsodyParams) -> np.ndarray:
    n = x.size
    # global lift
    env = np.linspace(0.85, float(pros.emotional_rise), n, dtype=np.float32) ** 1.58
    y = x * env

    # syllable/phrase shaping
    pc = max(1, int(pros.phrase_count))
    for i in range(pc):
        s0 = int((i * n) / pc)
        s1 = int(((i + 1) * n) / pc)
        if s1 <= s0:
            continue
        ph = (np.linspace(0.75, 1.0, s1 - s0, dtype=np.float32) ** 1.48)
        y[s0:s1] *= ph
    return y.astype(np.float32)


# =========================
# 6) Core engine
# =========================

class VivoxForgeCore:
    def __init__(self):
        self.profile = _detect_device_profile()
        self.voice_latents: Dict[str, np.ndarray] = {}
        print(
            f"✅ Vivox Forge v1.4.1 online | SR={self.profile.sr_out} | cores={self.profile.cpu_cores_physical} | RAM={self.profile.ram_gb:.1f}GB"
        )

    def register_voice(self, voice_id: str):
        # Deterministic-ish latent seed per voice_id for repeatability
        seed = (abs(hash(voice_id)) % (2**32 - 1))
        rng = np.random.RandomState(seed)
        # latent parameters: [pressure_bias, tension_bias, brightness_bias]
        latent = rng.randn(3).astype(np.float32) * 0.12
        self.voice_latents[voice_id] = latent
        print(f"🔒 Registered sovereign voice: {voice_id}")

    def sing(
        self,
        lyrics: str = "In the heart of the sovereign light, we rise forever",
        voice_id: str = "belel_prime",
        duration_ms: int = 9200,
        phoneme_sequence: Optional[List[Tuple[str, float, float]]] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Returns (audio_float32_mono, sample_rate).
        phoneme_sequence: list of (phoneme, relative_duration, base_f0_hz).
        """
        if voice_id not in self.voice_latents:
            self.register_voice(voice_id)

        sr = self.profile.sr_out
        n = int((duration_ms / 1000.0) * sr)
        n = max(n, 2048)

        if phoneme_sequence is None:
            # Default "ah"-centric phrase; lyrics are not parsed here.
            phoneme_sequence = [
                ("ih", 0.06, 218), ("n", 0.04, 222), ("th", 0.07, 226), ("uh", 0.10, 230),
                ("h", 0.05, 232), ("ah", 0.14, 238), ("r", 0.08, 242), ("t", 0.06, 246),
                ("uh", 0.07, 250), ("v", 0.05, 254), ("s", 0.06, 258), ("uh", 0.08, 262),
                ("v", 0.05, 266), ("r", 0.07, 270), ("n", 0.06, 274), ("ih", 0.09, 278),
                ("t", 0.07, 282), ("iy", 0.12, 285), ("f", 0.05, 280), ("ow", 0.10, 272),
                ("r", 0.08, 265), ("eh", 0.09, 255), ("v", 0.06, 245), ("eh", 0.11, 238),
                ("r", 0.08, 230),
            ]

        # Normalize relative durations to total
        rel_sum = sum(max(0.001, float(p[1])) for p in phoneme_sequence)
        phoneme_sequence = [(ph, float(d) / rel_sum, float(f0)) for (ph, d, f0) in phoneme_sequence]

        latent = self.voice_latents[voice_id]
        pressure_bias = float(latent[0])
        tension_bias = float(latent[1])
        bright_bias = float(latent[2])

        # Prosody params (can be tuned per voice)
        pros = ProsodyParams(
            vibrato_hz=5.8 + 0.15 * bright_bias,
            vibrato_depth_semitones=0.22 + 0.06 * max(0.0, tension_bias),
            jitter_rel_std=0.0032 + 0.0015 * max(0.0, -tension_bias),
            shimmer_rel_std=0.010 + 0.006 * max(0.0, pressure_bias),
            shimmer_rate_hz=7.2 + 0.5 * bright_bias,
            emotional_rise=1.22,
            phrase_count=10,
        )

        # LF params (stable, controllable)
        lf = LFParams(
            tp=0.40 + 0.03 * np.tanh(tension_bias),
            te=0.55 + 0.02 * np.tanh(pressure_bias),
            ta=0.12 + 0.02 * np.tanh(-bright_bias),
            tilt_db_per_oct=12.0 + 4.0 * max(0.0, -bright_bias),
        )

        audio = np.zeros(n, dtype=np.float32)

        # Prepare breath/noise bed
        breath = _pinkish_noise(n, sr, self.profile.breath_quality)
        t = np.arange(n, dtype=np.float32) / float(sr)
        breath_env = (0.55 + 0.45 * np.sin(2.0 * np.pi * 0.78 * t)).astype(np.float32)
        # Scale breath by profile
        breath_scale = 0.0025 if self.profile.is_low_power else 0.0068
        breath = breath * breath_env * float(breath_scale) * (1.0 + 0.25 * pressure_bias)

        # Chest component (subharmonic feel)
        chest = np.sin(2.0 * np.pi * 70.0 * t).astype(np.float32) * (0.0048 if self.profile.is_low_power else 0.0060)
        chest *= (0.8 + 0.2 * np.tanh(pressure_bias)).astype(np.float32)

        # Segment synthesis
        idx = 0
        bank: Optional[List[ResonatorSpec]] = None

        # Precompute per-block formant targets for the whole utterance
        f_targets: List[Tuple[float, float, float, float]] = []
        block = self.profile.block_size

        # Build segments and collect formant targets
        segments: List[Tuple[int, int, str, float]] = []  # (start,end,phoneme,base_f0)
        for ph, rel_dur, base_f0 in phoneme_sequence:
            seg_len = int(rel_dur * n)
            if seg_len < 64:
                seg_len = 64
            s0 = idx
            s1 = min(n, idx + seg_len)
            segments.append((s0, s1, ph, base_f0))
            idx = s1
            if idx >= n:
                break

        # Ensure last segment ends at n
        if segments and segments[-1][1] < n:
            s0, _, ph, f0 = segments[-1]
            segments[-1] = (s0, n, ph, f0)

        # Synthesize each segment into audio buffer
        for (s0, s1, ph, base_f0) in segments:
            seg_n = s1 - s0
            if seg_n <= 0:
                continue

            # Choose vowel identity for formant table; consonants use neutral
            key = ph if ph in FORMANT_TABLE else "neutral"
            f1, f2, f3, f4 = FORMANT_TABLE.get(key, FORMANT_TABLE["neutral"])

            # Build resonator bank once (states must persist across segments)
            if bank is None:
                bank = _make_resonator_bank(sr, f1, f2, f3, f4, self.profile.resonance_detail)

            # Prosody contours for this segment
            f0 = _make_f0_contour(base_f0, seg_n, sr, pros)
            am = _make_am_envelope(seg_n, sr, pros)

            # Pressure envelope (subglottal pressure proxy)
            tt = np.arange(seg_n, dtype=np.float32) / float(sr)
            pressure = (0.90 + 0.10 * np.sin(2.0 * np.pi * 0.65 * tt)).astype(np.float32)
            pressure *= (1.0 + 0.18 * np.tanh(pressure_bias)).astype(np.float32)

            # Excitation
            exc = _excitation_from_f0(f0, sr, pressure, lf)

            # Consonant noise injection (controlled)
            noise_mask = _consonant_noise_mask(ph, seg_n)
            if np.any(noise_mask > 0):
                nse = _pinkish_noise(seg_n, sr, "lite")
                # consonant energy scales with brightness
                nse_gain = 0.09 + 0.06 * max(0.0, bright_bias)
                exc = exc + (nse * noise_mask * float(nse_gain)).astype(np.float32)

            # Prepare per-block formant targets for this segment (smooth glides)
            seg_targets: List[Tuple[float, float, float, float]] = []
            seg_blocks = (seg_n + block - 1) // block
            # gentle drift to target formants (prevents static, helps realism)
            drift = 1.0 + 0.015 * np.sin(2.0 * np.pi * 0.4 * (np.arange(seg_blocks) / max(1, seg_blocks)))
            for bi in range(seg_blocks):
                seg_targets.append((f1 * drift[bi], f2 * drift[bi], f3 * drift[bi], f4 * drift[bi]))

            # Filter (real source->filter)
            filtered = _render_resonances_time_varying(
                exc, sr, bank, seg_targets, self.profile.block_size
            )

            # Apply AM shimmer and mild brightness/tension shaping
            # tension affects overall harmonic emphasis; we approximate via gentle pre-emphasis
            # (kept mild to avoid hiss)
            if tension_bias > 0.0:
                # simple pre-emphasis y[n]=x[n]-k*x[n-1]
                k = float(np.clip(0.85 + 0.08 * tension_bias, 0.75, 0.95))
                pre = np.empty_like(filtered)
                xm1 = 0.0
                for i in range(seg_n):
                    xi = float(filtered[i])
                    pre[i] = xi - k * xm1
                    xm1 = xi
                filtered = pre.astype(np.float32)

            seg = filtered * am

            # Mix into main buffer
            audio[s0:s1] += seg.astype(np.float32)

        # Add breath + chest bed
        audio += breath.astype(np.float32) + chest.astype(np.float32)

        # DC block + emotional envelope + soft clip normalization
        audio = _dc_block(audio, r=0.995).astype(np.float32)
        audio = _apply_emotional_envelope(audio, sr, pros).astype(np.float32)

        # Tail (room-ish fade)
        tail_s = 3.2 if self.profile.is_low_power else 3.6
        tail_n = int(tail_s * sr)
        tail = (np.linspace(1.0, 0.0, tail_n, dtype=np.float32) ** 3.2) * audio[-1] * 0.65
        audio = np.concatenate([audio, tail]).astype(np.float32)

        # Final safety: soft clip + headroom
        audio = _soft_clip(audio, drive=1.05).astype(np.float32) * 0.90

        print(f"🎤 Rendered SR={sr} Hz | profile={'LOW' if self.profile.is_low_power else 'HIGH'} | resonance={self.profile.resonance_detail}")
        return audio.astype(np.float32), sr


def _write_wav_mono_16(path: str, audio: np.ndarray, sr: int) -> None:
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm.tobytes())


if __name__ == "__main__":
    forge = VivoxForgeCore()
    forge.register_voice("belel_prime")
    wav, sr = forge.sing(
        lyrics="In the heart of the sovereign light, we rise forever",
        voice_id="belel_prime",
        duration_ms=9200,
        phoneme_sequence=None,  # supply your own for controlled pronunciation
    )
    out = "vivox_test_output.wav"
    _write_wav_mono_16(out, wav, sr)
    print(f"✅ Test file saved: {out}")
    print("   Play in VLC/Audacity. For 192k output, set: VIVOX_SR=192000")
