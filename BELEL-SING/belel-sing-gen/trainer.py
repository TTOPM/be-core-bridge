from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning import Trainer
from datetime import datetime
import argparse
import torch
import json
import matplotlib
import torch.nn.functional as F
import torch.utils.data
from pytorch_lightning.core import LightningModule
from torch.utils.data import DataLoader
from acestep.schedulers.scheduling_flow_match_euler_discrete import (
    FlowMatchEulerDiscreteScheduler,
)
from acestep.text2music_dataset import Text2MusicDataset
from loguru import logger
from transformers import AutoModel, Wav2Vec2FeatureExtractor
import torchaudio
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3 import (
    retrieve_timesteps,
)
from diffusers.utils.torch_utils import randn_tensor
from acestep.apg_guidance import apg_forward, MomentumBuffer
from tqdm import tqdm
import random
import os
from acestep.pipeline_ace_step import ACEStepPipeline

matplotlib.use("Agg")
torch.backends.cudnn.benchmark = False
torch.set_float32_matmul_precision("high")

class Pipeline(LightningModule):
    def __init__(
        self,
        learning_rate: float = 1e-4,
        num_workers: int = 4,
        T: int = 1000,
        weight_decay: float = 1e-2,
        every_plot_step: int = 2000,
        shift: float = 3.0,
        logit_mean: float = 0.0,
        logit_std: float = 1.0,
        timestep_densities_type: str = "logit_normal",
        ssl_coeff: float = 1.0,
        checkpoint_dir=None,
        max_steps: int = 200000,
        warmup_steps: int = 10,
        dataset_path: str = "./data/your_dataset_path",
        lora_config_path: str = None,
        adapter_name: str = "lora_adapter",
    ):
        super().__init__()

        self.save_hyperparameters()
        self.is_train = train
        self.T = T

        # Initialize scheduler
        self.scheduler = self.get_scheduler()

        # step 1: load model
        acestep_pipeline = ACEStepPipeline(checkpoint_dir)
        acestep_pipeline.load_checkpoint(acestep_pipeline.checkpoint_dir)

        transformers = acestep_pipeline.ace_step_transformer.float().cpu()
        transformers.enable_gradient_checkpointing()

        assert lora_config_path is not None, "Please provide a LoRA config path"
        if lora_config_path is not None:
            try:
                from peft import LoraConfig
            except ImportError:
                raise ImportError("Please install peft library to use LoRA training")
            with open(lora_config_path, encoding="utf-8") as f:
                import json
                lora_config = json.load(f)
            lora_config = LoraConfig(**lora_config)
            transformers.add_adapter(adapter_config=lora_config, adapter_name=adapter_name)
            self.adapter_name = adapter_name

        self.transformers = transformers

        self.dcae = acestep_pipeline.music_dcae.float().cpu()
        self.dcae.requires_grad_(False)

        self.text_encoder_model = acestep_pipeline.text_encoder_model.float().cpu()
        self.text_encoder_model.requires_grad_(False)
        self.text_tokenizer = acestep_pipeline.text_tokenizer

        if self.is_train:
            self.transformers.train()

            # download first
            try:
                self.mert_model = AutoModel.from_pretrained(
                    "m-a-p/MERT-v1-330M", trust_remote_code=True, cache_dir=checkpoint_dir
                ).eval()
            except:
                import json
                import os

                mert_config_path = os.path.join(
                    os.path.expanduser("~"),
                    ".cache",
                    "huggingface",
                    "hub",
                    "models--m-a-p--MERT-v1-330M",
                    "blobs",
                    "14f770758c7fe5c5e8ead4fe0f8e5fa727eb6942"
                )

                with open(mert_config_path) as f:
                    mert_config = json.load(f)
                mert_config["conv_pos_batch_norm"] = False
                with open(mert_config_path, mode="w") as f:
                    json.dump(mert_config, f)
                self.mert_model = AutoModel.from_pretrained(
                    "m-a-p/MERT-v1-330M", trust_remote_code=True, cache_dir=checkpoint_dir
                ).eval()
            self.mert_model.requires_grad_(False)
            self.resampler_mert = torchaudio.transforms.Resample(
                orig_freq=48000, new_freq=24000
            )
            self.processor_mert = Wav2Vec2FeatureExtractor.from_pretrained(
                "m-a-p/MERT-v1-330M", trust_remote_code=True
            )

            self.hubert_model = AutoModel.from_pretrained("utter-project/mHuBERT-147").eval()
            self.hubert_model.requires_grad_(False)
            self.resampler_mhubert = torchaudio.transforms.Resample(
                orig_freq=48000, new_freq=16000
            )
            self.processor_mhubert = Wav2Vec2FeatureExtractor.from_pretrained(
                "utter-project/mHuBERT-147",
                cache_dir=checkpoint_dir,
            )

            self.ssl_coeff = ssl_coeff

    def infer_mert_ssl(self, target_wavs, wav_lengths):
        # Input is N x 2 x T (48kHz), convert to N x T (24kHz), mono
        mert_input_wavs_mono_24k = self.resampler_mert(target_wavs.mean(dim=1))
        bsz = target_wavs.shape[0]
        actual_lengths_24k = wav_lengths // 2  # 48kHz -> 24kHz

        # Normalize the actual audio part
        means = torch.stack(
            [
                mert_input_wavs_mono_24k[i, : actual_lengths_24k[i]].mean()
                for i in range(bsz)
            ]
        )
        vars = torch.stack(
            [
                mert_input_wavs_mono_24k[i, : actual_lengths_24k[i]].var()
                for i in range(bsz)
            ]
        )
        mert_input_wavs_mono_24k = (
            mert_input_wavs_mono_24k - means.view(-1, 1)
        ) / torch.sqrt(vars.view(-1, 1) + 1e-7)

        # MERT SSL constraint
        # Define the length of each chunk (5 seconds of samples)
        chunk_size = 24000 * 5  # 5 seconds, 24000 samples per second
        total_length = mert_input_wavs_mono_24k.shape[1]

        num_chunks_per_audio = (actual_lengths_24k + chunk_size - 1) // chunk_size

        # Process chunks
        all_chunks = []
        chunk_actual_lengths = []
        for i in range(bsz):
            audio = mert_input_wavs_mono_24k[i]
            actual_length = actual_lengths_24k[i]
            for start in range(0, actual_length, chunk_size):
                end = min(start + chunk_size, actual_length)
                chunk = audio[start:end]
                if len(chunk) < chunk_size:
                    chunk = F.pad(
                        chunk, (0, chunk_size - len(chunk))
                    )  # Pad insufficient parts with zeros
                all_chunks.append(chunk)
                chunk_actual_lengths.append(end - start)

        # Stack all chunks to (total_chunks, chunk_size)
        all_chunks = torch.stack(all_chunks, dim=0)

        # Batch inference
        with torch.no_grad():
            # Output shape: (total_chunks, seq_len, hidden_size)
            mert_ssl_hidden_states = self.mert_model(all_chunks).last_hidden_state

        # Calculate the number of features for each chunk
        chunk_num_features = [(length + 319) // 320 for length in chunk_actual_lengths]

        # Trim the hidden states of each chunk
        chunk_hidden_states = [
            mert_ssl_hidden_states[i, : chunk_num_features[i], :]
            for i in range(len(all_chunks))
        ]

        # Organize hidden states by audio
        mert_ssl_hidden_states_list = []
        chunk_idx = 0
        for i in range(bsz):
            audio_chunks = chunk_hidden_states[
                chunk_idx : chunk_idx + num_chunks_per_audio[i]
            ]
            audio_hidden = torch.cat(
                audio_chunks, dim=0
            )  # Concatenate chunks of the same audio
            mert_ssl_hidden_states_list.append(audio_hidden)
            chunk_idx += num_chunks_per_audio[i]

        return mert_ssl_hidden_states_list

    def infer_mhubert_ssl(self, target_wavs, wav_lengths):
        # Step 1: Preprocess audio
        # Input: N x 2 x T (48kHz, stereo) -> N x T (16kHz, mono)
        mhubert_input_wavs_mono_16k = self.resampler_mhubert(target_wavs.mean(dim=1))
        bsz = target_wavs.shape[0]
        actual_lengths_16k = wav_lengths // 3  # Convert lengths from 48kHz to 16kHz

        # Step 2: Zero-mean unit-variance normalization (only on actual audio)
        means = torch.stack(
            [
                mhubert_input_wavs_mono_16k[i, : actual_lengths_16k[i]].mean()
                for i in range(bsz)
            ]
        )
        vars = torch.stack(
            [
                mhubert_input_wavs_mono_16k[i, : actual_lengths_16k[i]].var()
                for i in range(bsz)
            ]
        )
        mhubert_input_wavs_mono_16k = (
            mhubert_input_wavs_mono_16k - means.view(-1, 1)
        ) / torch.sqrt(vars.view(-1, 1) + 1e-7)

        # Step 3: Define chunk size for MHubert (30 seconds at 16kHz)
        chunk_size = 16000 * 30  # 30 seconds = 480,000 samples

        # Step 4: Split audio into chunks
        num_chunks_per_audio = (
            actual_lengths_16k + chunk_size - 1
        ) // chunk_size  # Ceiling division
        all_chunks = []
        chunk_actual_lengths = []

        for i in range(bsz):
            audio = mhubert_input_wavs_mono_16k[i]
            actual_length = actual_lengths_16k[i]
            for start in range(0, actual_length, chunk_size):
                end = min(start + chunk_size, actual_length)
                chunk = audio[start:end]
                if len(chunk) < chunk_size:
                    chunk = F.pad(chunk, (0, chunk_size - len(chunk)))  # Pad with zeros
                all_chunks.append(chunk)
                chunk_actual_lengths.append(end - start)

        # Step 5: Stack all chunks for batch inference
        all_chunks = torch.stack(all_chunks, dim=0)  # Shape: (total_chunks, chunk_size)

        # Step 6: Batch inference with MHubert model
        with torch.no_grad():
            mhubert_ssl_hidden_states = self.hubert_model(all_chunks).last_hidden_state
            # Shape: (total_chunks, seq_len, hidden_size)

        # Step 7: Compute number of features per chunk (assuming model stride of 320)
        chunk_num_features = [(length + 319) // 320 for length in chunk_actual_lengths]

        # Step 8: Trim hidden states to remove padding effects
        chunk_hidden_states = [
            mhubert_ssl_hidden_states[i, : chunk_num_features[i], :]
            for i in range(len(all_chunks))
        ]

        # Step 9: Reorganize hidden states by original audio
        mhubert_ssl_hidden_states_list = []
        chunk_idx = 0
        for i in range(bsz):
            audio_chunks = chunk_hidden_states[
                chunk_idx : chunk_idx + num_chunks_per_audio[i]
            ]
            audio_hidden = torch.cat(
                audio_chunks, dim=0
            )  # Concatenate chunks for this audio
            mhubert_ssl_hidden_states_list.append(audio_hidden)
            chunk_idx += num_chunks_per_audio[i]
        return mhubert_ssl_hidden_states_list

    def get_text_embeddings(self, texts, device, text_max_length=256):
        inputs = self.text_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=text_max_length,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        if self.text_encoder_model.device != device:
            self.text_encoder_model.to(device)
        with torch.no_grad():
            outputs = self.text_encoder_model(**inputs)
            last_hidden_states = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"]
        return last_hidden_states, attention_mask

    def preprocess(self, batch, train=True):
        target_wavs = batch["target_wavs"]
        wav_lengths = batch["wav_lengths"]

        dtype = target_wavs.dtype
        bs = target_wavs.shape[0]
        device = target_wavs.device

        # SSL constraints
        mert_ssl_hidden_states = None
        mhubert_ssl_hidden_states = None
        if train:
            with torch.amp.autocast(device_type="cuda", dtype=dtype):
                mert_ssl_hidden_states = self.infer_mert_ssl(target_wavs, wav_lengths)
                mhubert_ssl_hidden_states = self.infer_mhubert_ssl(
                    target_wavs, wav_lengths
                )

        # 1: text embedding
        texts = batch["prompts"]
        encoder_text_hidden_states, text_attention_mask = self.get_text_embeddings(
            texts, device
        )
        encoder_text_hidden_states = encoder_text_hidden_states.to(dtype)

        target_latents, _ = self.dcae.encode(target_wavs, wav_lengths)
        attention_mask = torch.ones(
            bs, target_latents.shape
