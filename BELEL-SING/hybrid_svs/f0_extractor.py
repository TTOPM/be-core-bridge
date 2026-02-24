cat > BELEL-SING/hybrid_svs/f0_extractor.py << 'EOF'
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover
    librosa = None


@dataclass(frozen=True)
class F0Cfg:
    sr: int = 24000
    hop: int = 256
    fmin: float = 60.0
    fmax: float = 1100.0


def _autocorr_f0(x: np.ndarray, cfg: F0Cfg) -> np.ndarray:
    # framewise autocorr pitch with voicing heuristic
    n = len(x)
    hop = cfg.hop
    win = hop * 4
    if n < win:
        pad = win - n
        x = np.pad(x, (0, pad))
        n = len(x)

    T = 1 + (n - win) // hop
    f0 = np.zeros((T,), dtype=np.float32)

    min_lag = int(cfg.sr / cfg.fmax)
    max_lag = int(cfg.sr / cfg.fmin)

    w = np.hanning(win).astype(np.float32)

    for t in range(T):
        s = t * hop
        frame = x[s:s + win] * w
        frame = frame - frame.mean()
        denom = np.sum(frame * frame) + 1e-8
        if denom < 1e-6:
            continue
        ac = np.correlate(frame, frame, mode="full")[win - 1:]
        ac[:min_lag] = 0.0
        ac[max_lag + 1:] = 0.0
        lag = int(np.argmax(ac))
        peak = float(ac[lag])
        # voicing check
        if peak / denom < 0.25:
            continue
        f0[t] = cfg.sr / max(lag, 1)

    return f0


def extract_f0(x: np.ndarray, cfg: F0Cfg) -> np.ndarray:
    """
    Returns f0 in Hz at hop rate, shape [T].
    Prefers librosa.pyin if installed (cleaner pitch/voicing), otherwise autocorr.
    """
    x = x.astype(np.float32)
    if librosa is not None:
        f0, voiced, _ = librosa.pyin(
            x,
            fmin=cfg.fmin,
            fmax=cfg.fmax,
            sr=cfg.sr,
            hop_length=cfg.hop,
        )
        f0 = np.nan_to_num(f0, nan=0.0).astype(np.float32)
        f0[~voiced] = 0.0
        return f0
    return _autocorr_f0(x, cfg)
EOF