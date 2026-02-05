# File: belel_sing_gen/belel_plugin_system.py
# Purpose: Dynamic plugin loader for community extensions
# Features:
#   - Auto-discovers and loads plugins from a directory
#   - Standard interface: process(audio_tensor, **kwargs) → audio_tensor
#   - Chain multiple plugins in order
#   - Isolated error handling per plugin
#   - Built-in example plugins (reverb, pitch shift, echo, normalize)
# Dependencies: torch, torchaudio, numpy, soundfile (optional)

import torch
import torchaudio
from pathlib import Path
import importlib.util
import sys
import os
from typing import List, Dict, Any, Optional
import numpy as np

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

PLUGIN_DIR = Path("plugins")               # Create this folder next to your scripts
PLUGIN_DIR.mkdir(exist_ok=True)

SAMPLE_RATE = 44100

# ────────────────────────────────────────────────
# BASE PLUGIN INTERFACE (all plugins must inherit this)
# ────────────────────────────────────────────────

class BELELPluginBase:
    """
    Abstract base class every plugin must inherit from.
    Implement only the process() method.
    """
    name: str = "unnamed_plugin"
    description: str = "No description"

    def process(self, audio: torch.Tensor, **kwargs) -> torch.Tensor:
        """
        Main method: take input waveform → return processed waveform
        audio shape: [channels, time] or [time] (mono)
        Must preserve sample rate and shape convention
        """
        raise NotImplementedError("Plugin must implement process()")

    def __str__(self):
        return f"{self.name}: {self.description}"

# ────────────────────────────────────────────────
# BUILT-IN EXAMPLE PLUGINS
# (users can add their own in the plugins/ folder)
# ────────────────────────────────────────────────

class ReverbPlugin(BELELPluginBase):
    name = "reverb"
    description = "Adds natural room reverb using convolution"

    def process(self, audio: torch.Tensor, amount: float = 0.4, room_size: float = 0.5, **kwargs) -> torch.Tensor:
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        # Impulse response: simple exponential decay (room simulation)
        ir_length = int(SAMPLE_RATE * 1.5)  # 1.5s tail
        ir = torch.exp(-torch.linspace(0, 5, ir_length)) * room_size
        ir = ir / ir.abs().max() * 0.8  # normalize

        # Convolve per channel
        processed = torch.zeros_like(audio)
        for ch in range(audio.shape[0]):
            conv = torch.nn.functional.conv1d(
                audio[ch:ch+1].unsqueeze(0),
                ir.unsqueeze(0).unsqueeze(0),
                padding=ir_length-1
            ).squeeze(0).squeeze(0)[:audio.shape[1]]
            processed[ch] = conv

        # Mix dry/wet
        wet = processed * amount
        dry = audio * (1 - amount)
        return wet + dry

class PitchShiftPlugin(BELELPluginBase):
    name = "pitch_shift"
    description = "Changes pitch without affecting tempo (phase vocoder style)"

    def process(self, audio: torch.Tensor, semitones: float = 2.0, **kwargs) -> torch.Tensor:
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        # Simple pitch shift via resample (approximation)
        speed_factor = 2 ** (semitones / 12.0)
        new_length = int(audio.shape[1] / speed_factor)

        shifted = torch.zeros(audio.shape[0], new_length, device=audio.device)
        for ch in range(audio.shape[0]):
            resampled = torchaudio.transforms.Resample(
                orig_freq=SAMPLE_RATE,
                new_freq=int(SAMPLE_RATE * speed_factor)
            )(audio[ch].unsqueeze(0)).squeeze(0)[:new_length]
            shifted[ch] = resampled

        return shifted.mean(dim=0) if shifted.shape[0] > 1 else shifted.squeeze(0)

class EchoPlugin(BELELPluginBase):
    name = "echo"
    description = "Adds repeating echo/delay effect"

    def process(self, audio: torch.Tensor, delay_sec: float = 0.3, feedback: float = 0.4, **kwargs) -> torch.Tensor:
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        delay_samples = int(delay_sec * SAMPLE_RATE)
        output = audio.clone()

        for _ in range(4):  # max 4 echoes
            delayed = torch.roll(output, shifts=delay_samples, dims=-1)
            delayed[..., :delay_samples] = 0  # clear wrap-around
            output = output + delayed * feedback
            feedback *= 0.6  # decay

        return output.mean(dim=0) if output.shape[0] > 1 else output.squeeze(0)

class NormalizePlugin(BELELPluginBase):
    name = "normalize"
    description = "Loudness normalization to target LUFS"

    def process(self, audio: torch.Tensor, target_lufs: float = -14.0, **kwargs) -> torch.Tensor:
        # Convert to pydub for LUFS estimation
        temp_wav = "temp_norm.wav"
        torchaudio.save(temp_wav, audio.unsqueeze(0) if audio.dim() == 1 else audio, SAMPLE_RATE)

        seg = AudioSegment.from_wav(temp_wav)
        current_lufs = seg.dBFS
        gain = target_lufs - current_lufs
        normalized = seg.apply_gain(gain)

        normalized.export(temp_wav, format="wav")
        waveform, _ = torchaudio.load(temp_wav)
        os.remove(temp_wav)

        return waveform.squeeze(0) if waveform.shape[0] == 1 else waveform.mean(dim=0)

# ────────────────────────────────────────────────
# PLUGIN LOADER & MANAGER
# ────────────────────────────────────────────────

class BELELPluginSystem:
    """
    Dynamic plugin loader:
    - Scans 'plugins/' folder
    - Loads any .py file that defines a class inheriting BELELPluginBase
    - Provides chaining and safe execution
    """

    def __init__(self, plugin_dir: str | Path = PLUGIN_DIR):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, BELELPluginBase] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Auto-discover and instantiate plugins"""
        sys.path.append(str(self.plugin_dir))

        for file in self.plugin_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue

            module_name = file.stem
            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find classes that inherit BELELPluginBase
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BELELPluginBase) and attr != BELELPluginBase:
                    plugin_instance = attr()
                    self.plugins[plugin_instance.name] = plugin_instance
                    print(f"Loaded plugin: {plugin_instance.name} ({plugin_instance.description})")

        sys.path.pop()

    def list_plugins(self) -> List[str]:
        """Return list of loaded plugin names"""
        return list(self.plugins.keys())

    def process_chain(
        self,
        audio: torch.Tensor,
        chain: List[Dict[str, Any]]  # [{"name": "reverb", "amount": 0.5}, {"name": "normalize"}]
    ) -> torch.Tensor:
        """
        Run a sequence of plugins in order.
        Each dict must have 'name' key + optional kwargs.
        """
        current = audio.clone()

        for step in chain:
            name = step.get("name")
            if name not in self.plugins:
                print(f"Warning: Plugin '{name}' not found — skipping")
                continue

            kwargs = {k: v for k, v in step.items() if k != "name"}
            try:
                current = self.plugins[name].process(current, **kwargs)
                print(f"Applied plugin: {name}")
            except Exception as e:
                print(f"Plugin '{name}' failed: {e} — continuing with previous audio")

        return current

    def apply_single(
        self,
        audio: torch.Tensor,
        plugin_name: str,
        **kwargs
    ) -> torch.Tensor:
        """Convenience: apply one plugin"""
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' not loaded")

        return self.plugins[plugin_name].process(audio, **kwargs)

# ────────────────────────────────────────────────
# CLI ENTRY POINT (demo usage)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BELEL Plugin System Demo")
    parser.add_argument("input", type=str, help="Input WAV file")
    parser.add_argument("--chain", nargs="+", help="Chain steps: plugin_name:key=value plugin_name ...")
    parser.add_argument("--list", action="store_true", help="List loaded plugins")
    parser.add_argument("--output", type=str, default="processed.wav")

    args = parser.parse_args()

    system = BELELPluginSystem()

    if args.list:
        print("Available plugins:")
        for name in system.list_plugins():
            print(f"  - {name}: {system.plugins[name].description}")
        sys.exit(0)

    # Load input
    audio, sr = torchaudio.load(args.input)
    if sr != SAMPLE_RATE:
        audio = torchaudio.transforms.Resample(sr, SAMPLE_RATE)(audio)
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0)

    # Parse chain
    chain = []
    if args.chain:
        for step in args.chain:
            parts = step.split(":")
            name = parts[0]
            kwargs = {}
            if len(parts) > 1:
                for kv in parts[1].split(","):
                    k, v = kv.split("=")
                    try:
                        v = float(v) if '.' in v else int(v)
                    except:
                        pass
                    kwargs[k] = v
            chain.append({"name": name, **kwargs})

    # Run chain
    processed = system.process_chain(audio, chain)

    # Save
    torchaudio.save(args.output, processed.unsqueeze(0) if processed.dim() == 1 else processed, SAMPLE_RATE)
    print(f"Processed audio saved to: {args.output}")
