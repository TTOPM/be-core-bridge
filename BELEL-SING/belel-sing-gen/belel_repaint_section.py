# File: belel_sing_gen/belel_repaint_section.py
# Purpose: Mask-based, prompt-driven section repainting with seamless blending
# Features:
#   - Select any time range (start_sec → end_sec)
#   - Regenerate section with new prompt (full, vocals-only, instr-only, or custom mask)
#   - Adjustable strength (blend original vs new)
#   - Crossfade overlap for artifact-free transitions
#   - Optional partial mask (vocals/instruments)
#   - Before/after spectrogram preview (optional)
# Dependencies: torch, torchaudio, pydub, numpy, matplotlib

import torch
import torchaudio
from pathlib import Path
from typing import Optional, Literal
from pydub import AudioSegment
import numpy as np
import matplotlib.pyplot as plt
import os

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

SAMPLE_RATE = 44100
DEFAULT_CROSSFADE_MS = 100               # Smooth transition duration
DEFAULT_STRENGTH = 0.85                  # Default replace intensity
PREVIEW_DIR = Path("repaint_previews")   # Where spectrograms are saved

PREVIEW_DIR.mkdir(exist_ok=True)

# Placeholder orchestrator — replace with your real BELELOrchestrator instance
class DummyOrchestrator:
    def orchestrate(self, prompt: str, duration_sec: float, **kwargs) -> torch.Tensor:
        # Returns dummy waveform of requested length (replace with real call)
        length = int(duration_sec * SAMPLE_RATE)
        return torch.randn(1, length) * 0.25  # quiet noise for testing

ORCHESTRATOR = DummyOrchestrator()  # <-- REPLACE WITH YOUR ACTUAL ORCHESTRATOR

# ────────────────────────────────────────────────
# CORE CLASS
# ────────────────────────────────────────────────

class BELELRepaintSection:
    """
    Advanced section repainting tool:
    - Time-range selection
    - Prompt-driven regeneration
    - Strength + crossfade blending
    - Partial mask support (vocals/instruments/full)
    - Optional before/after spectrogram preview
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
        Linear crossfade between original and new at boundaries.
        """
        if overlap_samples <= 0:
            return new

        fade_out = torch.linspace(1.0, 0.0, overlap_samples, device=original.device)
        fade_in  = torch.linspace(0.0, 1.0, overlap_samples, device=new.device)

        blended = original.clone()
        blended[-overlap_samples:] *= fade_out
        blended[-overlap_samples:] += new[:overlap_samples] * fade_in

        return blended

    def _save_spectrogram(
        self,
        waveform: torch.Tensor,
        filename: str,
        title: str = "Spectrogram"
    ):
        """Save mel spectrogram preview."""
        try:
            mel = torchaudio.transforms.MelSpectrogram(
                sample_rate=SAMPLE_RATE,
                n_fft=2048,
                hop_length=512,
                n_mels=128
            )(waveform.cpu())
            mel_db = 20 * torch.log10(mel + 1e-8)

            plt.figure(figsize=(10, 4))
            plt.imshow(mel_db.numpy(), origin='lower', aspect='auto', cmap='magma')
            plt.title(title)
            plt.ylabel('Mel Frequency')
            plt.xlabel('Time')
            plt.colorbar(format='%+2.0f dB')
            plt.tight_layout()
            plt.savefig(filename)
            plt.close()
            print(f"Spectrogram saved: {filename}")
        except Exception as e:
            print(f"Spectrogram failed: {e}")

    def repaint(
        self,
        input_audio: torch.Tensor | str | Path,
        start_sec: float,
        end_sec: float,
        new_prompt: str,
        strength: float = DEFAULT_STRENGTH,
        mask_type: Literal["full", "vocals-only", "instr-only"] = "full",
        overlap_ms: int = DEFAULT_CROSSFADE_MS,
        preview: bool = False,
        output_path: Optional[str | Path] = None
    ) -> torch.Tensor:
        """
        Repaint a specific time range in the audio.

        Args:
            input_audio:        waveform tensor or path to WAV file
            start_sec, end_sec: time range in seconds
            new_prompt:         prompt to regenerate the section
            strength:           blending factor (0.0 = original, 1.0 = full new)
            mask_type:          which part to repaint ("full", "vocals-only", "instr-only")
            overlap_ms:         crossfade duration in milliseconds
            preview:            save before/after spectrograms
            output_path:        optional save location

        Returns:
            Updated full waveform tensor
        """
        # ─── Load audio if path given ────────────────────────────────────────
        if isinstance(input_audio, (str, Path)):
            waveform, sr = torchaudio.load(str(input_audio))
            if sr != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
                waveform = resampler(waveform)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)  # to mono
            input_audio = waveform.to(torch.float32).squeeze(0)
        else:
            input_audio = input_audio.to(torch.float32)
            if input_audio.dim() > 1:
                input_audio = input_audio.mean(dim=0)

        total_samples = input_audio.shape[0]
        start_sample = max(0, int(start_sec * SAMPLE_RATE))
        end_sample   = min(total_samples, int(end_sec * SAMPLE_RATE))
        section_len  = end_sample - start_sample

        if section_len <= 0:
            raise ValueError("Invalid time range: end must be after start")

        # ─── Optional before preview ─────────────────────────────────────────
        if preview:
            self._save_spectrogram(
                input_audio,
                str(PREVIEW_DIR / "before_repaint.png"),
                "Before Repaint"
            )

        # ─── Extract original section ────────────────────────────────────────
        original_section = input_audio[start_sample:end_sample].clone()

        # ─── Generate new section ────────────────────────────────────────────
        new_section = self.orch.orchestrate(
            prompt=new_prompt,
            duration_sec=(end_sec - start_sec)
        ).squeeze(0)  # assume returns [1, length] → squeeze to [length]

        # Match exact length (resample if needed)
        if new_section.shape[0] != section_len:
            new_section = torchaudio.transforms.Resample(SAMPLE_RATE, SAMPLE_RATE)(
                new_section.unsqueeze(0)
            ).squeeze(0)[:section_len]

        # ─── Apply strength blending ─────────────────────────────────────────
        blended_section = original_section * (1 - strength) + new_section * strength

        # ─── Optional mask type (placeholder logic — replace with real stem sep)
        if mask_type != "full":
            print(f"Applying mask type: {mask_type}")
            if mask_type == "vocals-only":
                # Simulate: keep more original instruments
                blended_section = original_section * 0.4 + blended_section * 0.6
            elif mask_type == "instr-only":
                # Simulate: keep more original vocals
                blended_section = original_section * 0.7 + blended_section * 0.3

        # ─── Crossfade at boundaries ─────────────────────────────────────────
        overlap_samples = int(overlap_ms / 1000.0 * SAMPLE_RATE)

        # Left boundary crossfade
        if start_sample >= overlap_samples:
            left_start = start_sample - overlap_samples
            left_original = input_audio[left_start:start_sample]
            left_new = blended_section[:overlap_samples]
            left_blended = self._crossfade_blend(left_original, left_new, overlap_samples)
            input_audio[left_start:start_sample] = left_blended

        # Right boundary crossfade
        if end_sample + overlap_samples <= total_samples:
            right_start = end_sample
            right_end   = end_sample + overlap_samples
            right_original = input_audio[end_sample:right_end]
            right_new  = blended_section[-overlap_samples:]
            right_blended = self._crossfade_blend(right_new.flip(0), right_original.flip(0), overlap_samples).flip(0)
            input_audio[end_sample:right_end] = right_blended

        # ─── Replace main section ────────────────────────────────────────────
        input_audio[start_sample:end_sample] = blended_section

        # ─── Optional after preview ──────────────────────────────────────────
        if preview:
            self._save_spectrogram(
                input_audio,
                str(PREVIEW_DIR / "after_repaint.png"),
                "After Repaint"
            )

        # ─── Save if requested ───────────────────────────────────────────────
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
    parser.add_argument("input", type=str, help="Input WAV file path")
    parser.add_argument("--start", type=float, required=True, help="Start time (seconds)")
    parser.add_argument("--end", type=float, required=True, help="End time (seconds)")
    parser.add_argument("--prompt", type=str, required=True, help="New prompt for the section")
    parser.add_argument("--strength", type=float, default=0.85, help="Replace strength 0.0–1.0")
    parser.add_argument("--mask", choices=["full", "vocals-only", "instr-only"], default="full")
    parser.add_argument("--overlap_ms", type=int, default=100, help="Crossfade overlap (ms)")
    parser.add_argument("--preview", action="store_true", help="Save before/after spectrograms")
    parser.add_argument("--output", type=str, default=None, help="Output path (default: input_repaint.wav)")

    args = parser.parse_args()

    if args.output is None:
        p = Path(args.input)
        args.output = str(p.with_stem(p.stem + "_repainted"))

    tool = BELELRepaintSection()
    tool.repaint(
        input_audio=args.input,
        start_sec=args.start,
        end_sec=args.end,
        new_prompt=args.prompt,
        strength=args.strength,
        mask_type=args.mask,
        overlap_ms=args.overlap_ms,
        preview=args.preview,
        output_path=args.output
    )
