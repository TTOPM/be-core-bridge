cat > BELEL-SING/hybrid_svs/utils_audio.py << 'EOF'
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

try:
    import soundfile as sf  # type: ignore
except Exception:  # pragma: no cover
    sf = None

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover
    librosa = None


@dataclass(frozen=True)
class MelSpecCfg:
    sr: int = 24000
    n_fft: int = 1024
    hop: int = 256
    win: int = 1024
    n_mels: int = 80
    fmin: int = 40
    fmax: int = 11000


def load_wav(path: str, target_sr: int) -> np.ndarray:
    if sf is None:
        raise RuntimeError("soundfile not installed. pip install soundfile")
    x, sr = sf.read(path, always_2d=False)
    if x.ndim > 1:
        x = np.mean(x, axis=1)
    x = x.astype(np.float32)
    if sr != target_sr:
        if librosa is None:
            raise RuntimeError("librosa not installed for resampling. pip install librosa")
        x = librosa.resample(x, orig_sr=sr, target_sr=target_sr).astype(np.float32)
    x = np.clip(x, -1.0, 1.0)
    return x


def _mel_filterbank(cfg: MelSpecCfg) -> np.ndarray:
    if librosa is None:
        # fallback: triangular mel filterbank (basic)
        # This fallback is intentionally simple; for best results install librosa.
        def hz_to_mel(hz: float) -> float:
            return 2595.0 * math.log10(1.0 + hz / 700.0)

        def mel_to_hz(mel: float) -> float:
            return 700.0 * (10 ** (mel / 2595.0) - 1.0)

        n_freq = cfg.n_fft // 2 + 1
        mel_min = hz_to_mel(cfg.fmin)
        mel_max = hz_to_mel(cfg.fmax)
        mels = np.linspace(mel_min, mel_max, cfg.n_mels + 2)
        hz = mel_to_hz(mels)
        bins = np.floor((cfg.n_fft + 1) * hz / cfg.sr).astype(int)
        fb = np.zeros((cfg.n_mels, n_freq), dtype=np.float32)
        for m in range(cfg.n_mels):
            left, center, right = bins[m], bins[m + 1], bins[m + 2]
            left = max(left, 0); right = min(right, n_freq - 1)
            if center <= left: center = left + 1
            if right <= center: right = center + 1
            for k in range(left, center):
                fb[m, k] = (k - left) / (center - left)
            for k in range(center, right):
                fb[m, k] = (right - k) / (right - center)
        return fb
    else:
        fb = librosa.filters.mel(
            sr=cfg.sr,
            n_fft=cfg.n_fft,
            n_mels=cfg.n_mels,
            fmin=cfg.fmin,
            fmax=cfg.fmax,
        ).astype(np.float32)
        return fb


def mel_spectrogram(x: np.ndarray, cfg: MelSpecCfg) -> np.ndarray:
    # returns [T, n_mels]
    if torch is None:
        raise RuntimeError("torch required for mel_spectrogram")
    device = torch.device("cpu")
    xt = torch.from_numpy(x).to(device)

    window = torch.hann_window(cfg.win, device=device)
    stft = torch.stft(
        xt,
        n_fft=cfg.n_fft,
        hop_length=cfg.hop,
        win_length=cfg.win,
        window=window,
        center=True,
        return_complex=True,
    )
    mag = stft.abs().clamp_min(1e-7)  # [F, T]
    fb = torch.from_numpy(_mel_filterbank(cfg)).to(device)  # [M, F]
    mel = torch.matmul(fb, mag)  # [M, T]
    mel = mel.transpose(0, 1).contiguous()  # [T, M]
    mel = torch.log(mel).cpu().numpy().astype(np.float32)
    return mel


def griffin_lim(mel_log: np.ndarray, cfg: MelSpecCfg, n_iter: int = 32) -> np.ndarray:
    """
    Very lightweight fallback vocoder so inference always works.
    For best audio, you’ll later replace with a real neural vocoder.
    """
    if librosa is None:
        raise RuntimeError("librosa required for griffin_lim fallback. pip install librosa")
    fb = _mel_filterbank(cfg)  # [M, F]
    mel = np.exp(mel_log).astype(np.float32)  # [T, M]
    mel = mel.T  # [M, T]
    # pseudo-invert mel filterbank
    fb_t = fb.T
    denom = (fb @ fb_t) + 1e-6
    inv = fb_t / np.diag(denom)  # crude
    mag = np.maximum(1e-6, inv @ mel)  # [F, T]

    wav = librosa.griffinlim(
        mag,
        n_iter=n_iter,
        hop_length=cfg.hop,
        win_length=cfg.win,
        window="hann",
        center=True,
    )
    wav = wav.astype(np.float32)
    wav = wav / (np.max(np.abs(wav)) + 1e-8)
    return wav
EOF