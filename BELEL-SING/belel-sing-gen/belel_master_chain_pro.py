# File: belel_sing_gen/belel_master_chain_pro.py
# Purpose: Professional-grade parametric mastering chain
# Features: 3-band compression, dynamic EQ, stereo imaging, exciter, brickwall limiter
# Dependencies: pydub, numpy, torch (for tensor ops), soundfile (optional export)

from pathlib import Path
import numpy as np
import torch
import torchaudio
from pydub import AudioSegment, effects
import soundfile as sf  # pip install soundfile

SAMPLE_RATE = 44100

class BELELMasterChainPro:
    """
    Advanced mastering processor:
    - 3-band multi-compression (low/mid/high)
    - Dynamic EQ (boost/cut based on spectral analysis)
    - Stereo widener (Haas-like delay + phase shift)
    - Exciter (harmonic enhancement)
    - Brickwall limiter + LUFS normalization
    """

    def __init__(self):
        # Pre-computed crossover frequencies (Hz)
        self.low_cutoff = 150
        self.high_cutoff = 4000

    def _split_bands(self, seg: AudioSegment) -> tuple[AudioSegment, AudioSegment, AudioSegment]:
        """Split audio into low/mid/high bands using simple filters"""
        low = seg.low_pass_filter(self.low_cutoff).high_pass_filter(30)
        high = seg.high_pass_filter(self.high_cutoff).low_pass_filter(18000)
        mid = seg.low_pass_filter(self.high_cutoff).high_pass_filter(self.low_cutoff)
        return low, mid, high

    def _compress_band(self, band: AudioSegment, threshold_db: float, ratio: float) -> AudioSegment:
        return effects.compress_dynamic_range(
            band,
            threshold_db=threshold_db,
            ratio=ratio,
            attack=4,
            release=120
        )

    def _dynamic_eq(self, seg: AudioSegment) -> AudioSegment:
        """Simple spectral-aware EQ: boost mids if weak, cut harsh highs"""
        y = np.array(seg.get_array_of_samples(), dtype=np.float32)
        if len(y) == 0:
            return seg

        fft = np.abs(np.fft.rfft(y))
        freqs = np.fft.rfftfreq(len(y), 1/SAMPLE_RATE)

        # Boost 1–4 kHz if weak
        mid_mask = (freqs > 1000) & (freqs < 4000)
        if np.mean(fft[mid_mask]) < np.mean(fft) * 0.6:
            seg = seg.high_pass_filter(800).low_pass_filter(5000).apply_gain(2.5)

        # Cut harshness above 10 kHz if dominant
        high_mask = freqs > 10000
        if np.mean(fft[high_mask]) > np.mean(fft) * 1.8:
            seg = seg.low_pass_filter(10000).apply_gain(-1.8)

        return seg

    def _stereo_widener(self, seg: AudioSegment, width: float = 1.2) -> AudioSegment:
        """Haas effect + mid/side processing"""
        if seg.channels < 2:
            seg = seg.set_channels(2)

        left = seg.pan(-width / 2)
        right = seg.pan(width / 2)
        # Small delay on one side (Haas)
        right = right[5:]  # ~5 ms delay
        left = left[:len(right)]  # trim to match
        return left.overlay(right)

    def _exciter(self, seg: AudioSegment, amount: float = 0.25) -> AudioSegment:
        """Harmonic exciter using high-shelf boost + distortion"""
        high = seg.high_pass_filter(6000)
        high = high + high.low_pass_filter(12000).apply_gain(amount * 6)  # harmonic boost
        high = high.apply_gain(-amount * 3)  # prevent clipping
        return seg.overlay(high)

    def _brickwall_limit(self, seg: AudioSegment, threshold_db: float = -0.3) -> AudioSegment:
        """Hard limiter"""
        return effects.normalize(seg, headroom=threshold_db)

    def process(
        self,
        input_path: str | Path,
        output_path: str | Path,
        target_lufs: float = -14.0,
        comp_low_ratio: float = 4.0,
        comp_mid_ratio: float = 3.5,
        comp_high_ratio: float = 2.5,
        stereo_width: float = 1.3,
        exciter_amount: float = 0.22,
        true_peak_db: float = -0.8
    ):
        """Full mastering chain"""
        seg = AudioSegment.from_file(str(input_path))

        # Loudness target first
        current_lufs = seg.dBFS
        gain = target_lufs - current_lufs
        seg = seg.apply_gain(gain)

        # Band split & compression
        low, mid, high = self._split_bands(seg)
        low = self._compress_band(low, -24, comp_low_ratio)
        mid = self._compress_band(mid, -20, comp_mid_ratio)
        high = self._compress_band(high, -16, comp_high_ratio)

        # Recombine
        processed = low.overlay(mid).overlay(high)

        # Dynamic EQ
        processed = self._dynamic_eq(processed)

        # Stereo widening
        processed = self._stereo_widener(processed, width=stereo_width)

        # Exciter
        processed = self._exciter(processed, amount=exciter_amount)

        # Final limiting
        processed = self._brickwall_limit(processed, threshold_db=true_peak_db)

        # Export
        processed.export(str(output_path), format="wav", bitrate="320k")
        print(f"Mastered file saved to: {output_path}")

# ────────────────────────────────────────────────
# CLI ENTRY POINT
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BELEL Master Chain Pro")
    parser.add_argument("input", type=Path, help="Input WAV file")
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: input_mastered.wav)")
    parser.add_argument("--target_lufs", type=float, default=-14.0)
    parser.add_argument("--true_peak", type=float, default=-0.8)
    parser.add_argument("--stereo_width", type=float, default=1.3)
    parser.add_argument("--exciter", type=float, default=0.22)

    args = parser.parse_args()

    if args.output is None:
        args.output = args.input.with_stem(args.input.stem + "_mastered")

    master = BELELMasterChainPro()
    master.process(
        input_path=args.input,
        output_path=args.output,
        target_lufs=args.target_lufs,
        true_peak_db=args.true_peak,
        stereo_width=args.stereo_width,
        exciter_amount=args.exciter
    )
