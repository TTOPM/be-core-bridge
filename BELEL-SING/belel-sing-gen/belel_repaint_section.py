# File: belel_sing_gen/belel_repaint_section.py
# Purpose: Mask-based, prompt-driven section repainting with seamless blending
# Features:
#   - Select any time range (start_sec → end_sec)
#   - Regenerate section with new prompt (full, vocals-only, instruments-only)
#   - Adjustable mask strength (blend original vs new)
#   - Crossfade overlap for artifact-free transitions
#   - Optional partial mask (vocals/instruments)
# Dependencies: torch, torchaudio, pydub, numpy

import torch
import torchaudio
from pathlib import Path
from typing import Optional
from pydub import AudioSegment
import numpy as np

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

SAMPLE_RATE = 44100
CROSSFADE_MS = 80               # Overlap duration in ms for smooth transitions
DEFAULT_STRENGTH = 0.85         # 0.0 = keep original, 1.0 = full replace

# Assume orchestrator is available for regeneration
# Replace DummyOrchestrator with your real BELELOrchestrator instance
class DummyOrchestrator:
    def orchestrate(self, prompt: str, duration_sec: float, **kwargs) -> torch.Tensor:
        # Placeholder: returns random waveform of requested length
        length = int(duration_sec * SAMPLE_RATE)
        return torch.randn(1, length) * 0.3  # quiet random noise

ORCHESTRATOR = DummyOrchestrator()  # <-- REPLACE WITH YOUR REAL ORCHESTRATOR INSTANCE

# ────────────────────────────────────────────────
# CORE CLASS
# ────────────────────────────────────────────────

class BELELRepaintSection:
    """
    Precise section repainting:
    - Choose time range
    - Regenerate with new prompt
    - Blend with original using strength + crossfade
    - Optional: repaint only vocals or instruments (via mask)
    """

    def __init__(self, orchestrator=ORCHESTRATOR):
        self.orch = orchestrator

    def _crossfade_blend(
        self,
        original: torch.Tensor,
        new: torch.Tensor,
        overlap_samples: int
    ) -> torch.Tensor:
        """
        Smooth crossfade between original and new segment.
        Linear fade-out of original + fade-in of new.
        """
        if overlap_samples <= 0:
            return new

        fade_out = torch.linspace(1.0, 0.0, overlap_samples, device=original.device)
        fade_in = torch.linspace(0.0, 1.0, overlap_samples, device=new.device)

        blended = original.clone()
        blended[-overlap_samples:] *= fade_out
        blended[-overlap_samples:] += new[:overlap_samples] * fade_in

        return blended

    def repaint(
        self,
        input_audio: torch.Tensor | str | Path,
        start_sec: float,
        end_sec: float,
        new_prompt: str,
        strength: float = DEFAULT_STRENGTH,
        mask_type: str = "full",              # "full", "vocals-only", "instr-only"
        overlap_ms: int = CROSSFADE_MS,
        output_path: Optional[str | Path] = None
    ) -> torch.Tensor:
        """
        Repaint a specific section of the audio.

        Args:
            input_audio:        waveform tensor or path to WAV
            start_sec, end_sec: time range in seconds
            new_prompt:         prompt for regenerating the section
            strength:           0.0 = keep original, 1.0 = full new
            mask_type:          "full", "vocals-only", "instr-only"
            overlap_ms:         crossfade duration (ms)
            output_path:        optional save path

        Returns:
            Updated full waveform tensor
        """
        # Load audio if path given
        if isinstance(input_audio, (str, Path)):
            waveform, sr = torchaudio.load(str(input_audio))
            if sr != SAMPLE_RATE:
                waveform = torchaudio.transforms.Resample(sr, SAMPLE_RATE)(waveform)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            input_audio = waveform.to(torch.float32)

        input_audio = input_audio.squeeze(0) if input_audio.dim() > 1 else input_audio
        total_samples = input_audio.shape[0]
        sr = SAMPLE_RATE

        start_sample = int(start_sec * sr)
        end_sample = int(end_sec * sr)
        section_len = end_sample - start_sample

        if start_sample < 0 or end_sample > total_samples or section_len <= 0:
            raise ValueError("Invalid time range")

        # Extract original section
        original_section = input_audio[start_sample:end_sample]

        # Generate new section
        new_section = self.orch.orchestrate(
            prompt=new_prompt,
            duration_sec=(end_sec - start_sec)
        ).squeeze(0)  # assume returns [1, length]

        # Match length
        if new_section.shape[0] != section_len:
            new_section = torchaudio.transforms.Resample(SAMPLE_RATE, SAMPLE_RATE)(
                new_section.unsqueeze(0)
            ).squeeze(0)[:section_len]

        # Apply strength
        blended_section = original_section * (1 - strength) + new_section * strength

        # Optional mask type (placeholder — real impl would use stem separation)
        if mask_type != "full":
            print(f"Mask type '{mask_type}' requested — applying placeholder logic")
            # In production: separate stems → apply only to desired part
            if mask_type == "vocals-only":
                blended_section = original_section * 0.5 + blended_section * 0.5  # sim
            elif mask_type == "instr-only":
                blended_section = original_section * 0.7 + blended_section * 0.3

        # Crossfade at boundaries
        overlap_samples = int(overlap_ms / 1000 * sr)

        # Left crossfade (into section)
        if start_sample > overlap_samples:
            left_start = start_sample - overlap_samples
            left_end = start_sample
            left_original = input_audio[left_start:left_end]
            left_new = blended_section[:overlap_samples]
            left_blended = self._crossfade_blend(left_original, left_new, overlap_samples)
            input_audio[left_start:left_end] = left_blended

        # Right crossfade (out of section)
        if end_sample + overlap_samples < total_samples:
            right_start = end_sample
            right_end = end_sample + overlap_samples
            right_original = input_audio[right_start:right_end]
            right_new = blended_section[-overlap_samples:]
            right_blended = self._crossfade_blend(right_new.flip(0), right_original.flip(0), overlap_samples).flip(0)
            input_audio[right_start:right_end] = right_blended

        # Replace main section
        input_audio[start_sample:end_sample] = blended_section

        # Optional save
        if output_path:
            output_path = Path(output_path)
            torchaudio.save(str(output_path), input_audio.unsqueeze(0), SAMPLE_RATE)
            print(f"Repainted audio saved to: {output_path}")

        return input_audio

# ────────────────────────────────────────────────
# CLI ENTRY POINT
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BELEL Section Repaint Tool")
    parser.add_argument("input", type=str, help="Input WAV file")
    parser.add_argument("--start", type=float, required=True, help="Start time (seconds)")
    parser.add_argument("--end", type=float, required=True, help="End time (seconds)")
    parser.add_argument("--prompt", type=str, required=True, help="New prompt for section")
    parser.add_argument("--strength", type=float, default=0.85, help="Replace strength (0–1)")
    parser.add_argument("--mask", choices=["full", "vocals-only", "instr-only"], default="full")
    parser.add_argument("--overlap_ms", type=int, default=80, help="Crossfade overlap (ms)")
    parser.add_argument("--output", type=str, default=None, help="Output path (default: input_repaint.wav)")

    args = parser.parse_args()

    if args.output is None:
        p = Path(args.input)
        args.output = str(p.with_stem(p.stem + "_repainted"))

    repaint = BELELRepaintSection()
    repaint.repaint(
        input_audio=args.input,
        start_sec=args.start,
        end_sec=args.end,
        new_prompt=args.prompt,
        strength=args.strength,
        mask_type=args.mask,
        overlap_ms=args.overlap_ms,
        output_path=args.output
    )
