import io
import math
import wave
from typing import Iterable


def _clamp16(x: float) -> int:
    x = max(-1.0, min(1.0, x))
    return int(x * 32767)


def render_sine_melody_wav(
    seconds: int,
    sample_rate: int = 22050,
    base_freq: float = 220.0,
    watermark_gain: float = 0.06,
) -> bytes:
    """
    Synthetic demo audio: a short "melody" so the public can hear output,
    even when no internal checkpoints are connected.
    """
    total = int(seconds * sample_rate)

    # Simple stepped melody (pentatonic-ish)
    scale = [1.0, 1.122, 1.26, 1.498, 1.681]  # rough ratios
    step_len = max(1, total // (len(scale) * 2))

    frames = bytearray()
    for n in range(total):
        step = (n // step_len) % len(scale)
        freq = base_freq * scale[step]

        # mild vibrato
        vib = 1.0 + 0.01 * math.sin(2 * math.pi * 5.0 * (n / sample_rate))

        # main tone
        y = 0.25 * math.sin(2 * math.pi * (freq * vib) * (n / sample_rate))

        # watermark chirp every ~0.5s (low amplitude)
        chirp = watermark_gain * math.sin(2 * math.pi * 1800.0 * (n / sample_rate)) if (n % (sample_rate // 2) < 400) else 0.0

        s = _clamp16(y + chirp)
        frames += int(s).to_bytes(2, byteorder="little", signed=True)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return buf.getvalue()
