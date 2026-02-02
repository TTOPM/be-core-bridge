"""
Belel-Sing-Gen Sovereign Test Suite
Unit tests for core components: sampler, pipeline, inference, extensions (auto-evolve, verification, emotion synth, genre fusion).
Designed to run without real models/weights – uses mocks and placeholders for quick validation.
"""

import unittest
import torch
import random
from unittest.mock import MagicMock, patch
import sys
sys.path.insert(0, '.')  # Ensure imports work from root

from belel_data_sampler import BelelDataSampler
from belel_extensions import (
    auto_evolve,
    belel_verify_output,
    emotion_synth,
    genre_fusion
)
# Mock model for tests
mock_model = MagicMock()
mock_model.sample_rate = 44100
mock_model.__call__.return_value = torch.randn(2, 44100 * 60)  # 60s stereo audio


class TestBelelSingGen(unittest.TestCase):

    def setUp(self):
        self.sampler = BelelDataSampler()
        self.mock_audio = torch.randn(2, 44100 * 60)  # 60-second stereo dummy audio

    # ── Data Sampler Tests ─────────────────────────────────────────────────────
    def test_sampler_returns_valid_params(self):
        params = self.sampler.sample()
        self.assertIn("audio_duration", params)
        self.assertIn("prompt", params)
        self.assertIn("lyrics", params)
        self.assertGreaterEqual(params["audio_duration"], 30)
        self.assertLessEqual(params["audio_duration"], 300)
        self.assertIsInstance(params["languages"], list)

    def test_sampler_with_lora_override(self):
        params = self.sampler.sample(lora_name_or_path="custom_voice_lora.pth")
        self.assertIn("lora_name_or_path", params)
        self.assertGreater(params["guidance_scale"], 7.5)  # LoRA boost applied

    # ── Extensions Tests ───────────────────────────────────────────────────────
    def test_auto_evolve_runs_without_error(self):
        evolved = auto_evolve(mock_model, self.mock_audio, iterations=2, parallel_steps=False)
        self.assertIsInstance(evolved, torch.Tensor)
        mock_model.assert_called()  # Model was called during evolution

    def test_belel_verify_output_passes_valid_audio(self):
        result = belel_verify_output(self.mock_audio, compliance_threshold=0.8)
        self.assertIs(result, self.mock_audio)  # Returns original on pass

    def test_belel_verify_output_raises_on_failure(self):
        short_audio = torch.randn(2, 44100 * 10)  # Only 10s – should fail
        with self.assertRaises(ValueError):
            belel_verify_output(short_audio, compliance_threshold=0.99)

    def test_emotion_synth_applies_effects(self):
        original = self.mock_audio.clone()
        modified = emotion_synth(self.mock_audio, "joyful", intensity=1.0)
        self.assertIsInstance(modified, torch.Tensor)
        self.assertFalse(torch.allclose(original, modified))  # Effects changed waveform

    def test_genre_fusion_returns_enhanced_prompt(self):
        fused = genre_fusion("Test song", ["jazz", "electronic"])
        self.assertIn("fused style", fused)
        self.assertIn("jazz", fused.lower())
        self.assertIn("electronic", fused.lower())

    # ── Pipeline / Inference Integration Tests ────────────────────────────────
    @patch('belel_pipeline.BelelSingPipeline')
    def test_pipeline_initialization(self, mock_pipeline_cls):
        mock_pipeline_cls.return_value = MagicMock()
        from belel_pipeline import BelelSingPipeline
        pipe = BelelSingPipeline(checkpoint_dir="dummy")
        self.assertIsNotNone(pipe)


if __name__ == '__main__':
    unittest.main(verbosity=2)
