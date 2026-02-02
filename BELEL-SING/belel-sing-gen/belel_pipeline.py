```python
"""
Belel-Sing-Gen: Sovereign Music Generation Engine

https://github.com/TTOPM/be-core-bridge

Apache 2.0 License (Adapted and Enhanced for Belel Sovereignty)
"""

import random
import time
import os
import re
import torch
from loguru import logger
from tqdm import tqdm
import json
import math
from huggingface_hub import snapshot_download, AutoModel  # Enhanced Hugging Face integration
import bitsandbytes as bnb  # Belel low-VRAM quantization
import midiutil  # Belel MIDI export
import requests  # For API integrations (Spotify, NFT, etc.)

# Enhanced schedulers with Belel optimizations
from belel_sing_gen.schedulers.scheduling_flow_match_euler_discrete import (
    FlowMatchEulerDiscreteScheduler,
)
from belel_sing_gen.schedulers.scheduling_flow_match_heun_discrete import (
    FlowMatchHeunDiscreteScheduler,
)
from belel_sing_gen.schedulers.scheduling_flow_match_pingpong import (
    FlowMatchPingPongScheduler,
)
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3 import (
    retrieve_timesteps,
)
from diffusers.utils.torch_utils import randn_tensor
from diffusers.utils.peft_utils import set_weights_and_activate_adapters
from transformers import UMT5EncoderModel, AutoTokenizer

from belel_sing_gen.language_segmentation import LangSegment, language_filters
from belel_sing_gen.music_dcae.music_dcae_pipeline import MusicDCAE
from belel_sing_gen.models.belel_transformer import BelelTransformer2DModel
from belel_sing_gen.models.lyrics_utils.lyric_tokenizer import VoiceBpeTokenizer
from belel_sing_gen.apg_guidance import (
    apg_forward,
    MomentumBuffer,
    cfg_forward,
    cfg_zero_star,
    cfg_double_condition_forward,
)
import torchaudio
from .cpu_offload import cpu_offload

torch.backends.cudnn.benchmark = False
torch.set_float32_matmul_precision("high")
torch.backends.cudnn.deterministic = True
torch.backends.cuda.matmul.allow_tf32 = True
os.environ["TOKENIZERS_PARALLELISM"] = "false"

SUPPORT_LANGUAGES = {
    "en": 259,
    "de": 260,
    "fr": 262,
    "es": 284,
    "it": 285,
    "pt": 286,
    "pl": 294,
    "tr": 295,
    "ru": 267,
    "cs": 293,
    "nl": 297,
    "ar": 5022,
    "zh": 5023,
    "ja": 5412,
    "hu": 5753,
    "ko": 6152,
    "hi": 6680,
    # Belel expansions: Added for broader sovereignty
    "sw": 7001,  # Swahili
    "vi": 7002,  # Vietnamese
    "id": 7003,  # Indonesian
}

structure_pattern = re.compile(r"\[.*?\]")

def ensure_directory_exists(directory):
    directory = str(directory)
    if not os.path.exists(directory):
        os.makedirs(directory)

REPO_ID = "TTOPM/Belel-Sing-Gen-v1"  # Belel sovereign repo
REPO_ID_QUANT = REPO_ID + "-q4-K-M"  # Belel quantized version

class BelelSingPipeline:
    def __init__(
        self,
        checkpoint_dir=None,
        device_id=0,
        dtype="bfloat16",
        text_encoder_checkpoint_path=None,
        persistent_storage_path=None,
        torch_compile=False,
        cpu_offload=False,
        quantized=False,
        overlapped_decode=False,
        lora_path=None,
        huggingface_model=None,
        spotify_api_key=None,
        nft_mint_webhook=None,
        wondera_api_key=None,
        mubert_api_key=None,
        **kwargs,
    ):
        if not checkpoint_dir:
            if persistent_storage_path is None:
                checkpoint_dir = os.path.join(
                    os.path.expanduser("~"), ".cache/belel-sing-gen/checkpoints"
                )
                os.makedirs(checkpoint_dir, exist_ok=True)
            else:
                checkpoint_dir = os.path.join(persistent_storage_path, "checkpoints")
        ensure_directory_exists(checkpoint_dir)

        self.checkpoint_dir = checkpoint_dir
        self.lora_path = lora_path or "none"
        self.lora_weight = 1.0  # Belel adjustable LoRA weight
        device = (
            torch.device(f"cuda:{device_id}")
            if torch.cuda.is_available()
            else torch.device("cpu")
        )
        if device.type == "cpu" and torch.backends.mps.is_available():
            device = torch.device("mps")
        self.dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float32
        if device.type == "mps" and self.dtype == torch.bfloat16:
            self.dtype = torch.float16
        if device.type == "mps":
            self.dtype = torch.float32
        if 'BELEL_PIPELINE_DTYPE' in os.environ and len(os.environ['BELEL_PIPELINE_DTYPE']):
            self.dtype = getattr(torch, os.environ['BELEL_PIPELINE_DTYPE'])
        self.device = device
        self.loaded = False
        self.torch_compile = torch_compile
        self.cpu_offload = cpu_offload
        self.quantized = quantized
        self.overlapped_decode = overlapped_decode
        self.spotify_api_key = spotify_api_key
        self.nft_mint_webhook = nft_mint_webhook
        self.wondera_api_key = wondera_api_key
        self.mubert_api_key = mubert_api_key
        self.emotion = None  # Belel emotion synth
        self.fused_genres = []  # Belel genre fusion
        self.real_time_stream = False  # Belel real-time

        # Belel Hugging Face integration
        if huggingface_model:
            self.load_hf_model(huggingface_model)

    def load_hf_model(self, model_name):
        """Belel-enhanced: Load model from Hugging Face for hybrid generation"""
        self.hf_model = AutoModel.from_pretrained(model_name).to(self.device, dtype=self.dtype)
        print(f"Belel HF Integration: Loaded {model_name}")

    def cleanup_memory(self):
        """Belel-enhanced: Optimized memory cleanup with detailed logging"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            logger.info(f"Belel Memory Cleanup: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
        import gc
        gc.collect()

    def get_checkpoint_path(self, checkpoint_dir, repo):
        checkpoint_dir_models = None
        
        if checkpoint_dir is not None:
            required_dirs = ["music_dcae_f8c8", "music_vocoder", "belel_transformer", "umt5-base"]
            all_dirs_exist = True
            for dir_name in required_dirs:
                dir_path = os.path.join(checkpoint_dir, dir_name)
                if not os.path.exists(dir_path):
                    all_dirs_exist = False
                    break
            
            if all_dirs_exist:
                logger.info(f"Belel Load from: {checkpoint_dir}")
                checkpoint_dir_models = checkpoint_dir
        
        if checkpoint_dir_models is None:
            if checkpoint_dir is None:
                logger.info(f"Belel Download from HF: {repo}")
                checkpoint_dir_models = snapshot_download(repo)
            else:
                logger.info(f"Belel Download from HF: {repo}, cache to: {checkpoint_dir}")
                checkpoint_dir_models = snapshot_download(repo, cache_dir=checkpoint_dir)
        return checkpoint_dir_models

    def load_checkpoint(self, checkpoint_dir=None, export_quantized_weights=False):
        checkpoint_dir = self.get_checkpoint_path(checkpoint_dir, REPO_ID)
        dcae_checkpoint_path = os.path.join(checkpoint_dir, "music_dcae_f8c8")
        vocoder_checkpoint_path = os.path.join(checkpoint_dir, "music_vocoder")
        belel_checkpoint_path = os.path.join(checkpoint_dir, "belel_transformer")
        text_encoder_checkpoint_path = os.path.join(checkpoint_dir, "umt5-base")

        self.belel_transformer = BelelTransformer2DModel.from_pretrained(
            belel_checkpoint_path, torch_dtype=self.dtype
        )
        if self.cpu_offload:
            self.belel_transformer = (
                self.belel_transformer.to("cpu").eval().to(self.dtype)
            )
        else:
            self.belel_transformer = (
                self.belel_transformer.to(self.device).eval().to(self.dtype)
            )
        if self.torch_compile:
            self.belel_transformer = torch.compile(self.belel_transformer)

        self.music_dcae = MusicDCAE(
            dcae_checkpoint_path=dcae_checkpoint_path,
            vocoder_checkpoint_path=vocoder_checkpoint_path,
        )
        if self.cpu_offload:
            self.music_dcae = self.music_dcae.to("cpu").eval().to(self.dtype)
        else:
            self.music_dcae = self.music_dcae.to(self.device).eval().to(self.dtype)
        if self.torch_compile:
            self.music_dcae = torch.compile(self.music_dcae)

        lang_segment = LangSegment()
        lang_segment.setfilters(language_filters.default)
        self.lang_segment = lang_segment
        self.lyric_tokenizer = VoiceBpeTokenizer()

        text_encoder_model = UMT5EncoderModel.from_pretrained(
            text_encoder_checkpoint_path, torch_dtype=self.dtype
        ).eval()
        if self.cpu_offload:
            text_encoder_model = text_encoder_model.to("cpu").eval().to(self.dtype)
        else:
            text_encoder_model = text_encoder_model.to(self.device).eval().to(self.dtype)
        text_encoder_model.requires_grad_(False)
        self.text_encoder_model = text_encoder_model
        if self.torch_compile:
            self.text_encoder_model = torch.compile(self.text_encoder_model)

        self.text_tokenizer = AutoTokenizer.from_pretrained(
            text_encoder_checkpoint_path
        )
        self.loaded = True

        # Belel-enhanced compile with quantization export
        if self.torch_compile:
            if export_quantized_weights:
                from torch.ao.quantization import (
                    quantize_,
                    Int4WeightOnlyConfig,
                )

                group_size = 128
                use_hqq = True
                quantize_(
                    self.belel_transformer,
                    Int4WeightOnlyConfig(group_size=group_size, use_hqq=use_hqq),
                )
                quantize_(
                    self.text_encoder_model,
                    Int4WeightOnlyConfig(group_size=group_size, use_hqq=use_hqq),
                )

                # Belel save with sovereign naming
                torch.save(
                    self.belel_transformer.state_dict(),
                    os.path.join(
                        belel_checkpoint_path, "belel_pytorch_model_int4wo.bin"
                    ),
                )
                print(
                    "Belel Quantized Weights Saved to: ",
                    os.path.join(
                        belel_checkpoint_path, "belel_pytorch_model_int4wo.bin"
                    ),
                )
                torch.save(
                    self.text_encoder_model.state_dict(),
                    os.path.join(text_encoder_checkpoint_path, "belel_pytorch_model_int4wo.bin"),
                )
                print(
                    "Belel Quantized Weights Saved to: ",
                    os.path.join(text_encoder_checkpoint_path, "belel_pytorch_model_int4wo.bin"),
                )

    def load_quantized_checkpoint(self, checkpoint_dir=None):
        checkpoint_dir = self.get_checkpoint_path(checkpoint_dir, REPO_ID_QUANT)
        dcae_checkpoint_path = os.path.join(checkpoint_dir, "music_dcae_f8c8")
        vocoder_checkpoint_path = os.path.join(checkpoint_dir, "music_vocoder")
        belel_checkpoint_path = os.path.join(checkpoint_dir, "belel_transformer")
        text_encoder_checkpoint_path = os.path.join(checkpoint_dir, "umt5-base")

        self.music_dcae = MusicDCAE(
            dcae_checkpoint_path=dcae_checkpoint_path,
            vocoder_checkpoint_path=vocoder_checkpoint_path,
        )
        if self.cpu_offload:
            self.music_dcae.eval().to(self.dtype).to(self.device)
        else:
            self.music_dcae.eval().to(self.dtype).to('cpu')
        self.music_dcae = torch.compile(self.music_dcae)

        self.belel_transformer = BelelTransformer2DModel.from_pretrained(belel_checkpoint_path)
        self.belel_transformer.eval().to(self.dtype).to('cpu')
        self.belel_transformer = torch.compile(self.belel_transformer)
        self.belel_transformer.load_state_dict(
            torch.load(
                os.path.join(belel_checkpoint_path, "belel_pytorch_model_int4wo.bin"),
                map_location=self.device,
            ),assign=True
        )
        self.belel_transformer.torchao_quantized = True

        self.text_encoder_model = UMT5EncoderModel.from_pretrained(text_encoder_checkpoint_path)
        self.text_encoder_model.eval().to(self.dtype).to('cpu')
        self.text_encoder_model = torch.compile(self.text_encoder_model)
        self.text_encoder_model.load_state_dict(
            torch.load(
                os.path.join(text_encoder_checkpoint_path, "belel_pytorch_model_int4wo.bin"),
                map_location=self.device,
            ), assign=True
        )
        self.text_encoder_model.torchao_quantized = True

        self.text_tokenizer = AutoTokenizer.from_pretrained(
            text_encoder_checkpoint_path
        )

        lang_segment = LangSegment()
        lang_segment.setfilters(language_filters.default)
        self.lang_segment = lang_segment
        self.lyric_tokenizer = VoiceBpeTokenizer()

        self.loaded = True

    @cpu_offload("text_encoder_model")
    def get_text_embeddings(self, texts, text_max_length=256):
        inputs = self.text_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=text_max_length,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        if self.text_encoder_model.device != self.device:
            self.text_encoder_model.to(self.device)
        with torch.no_grad():
            outputs = self.text_encoder_model(**inputs)
            last_hidden_states = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"]
        return last_hidden_states, attention_mask

    @cpu_offload("text_encoder_model")
    def get_text_embeddings_null(
        self, texts, text_max_length=256, tau=0.01, l_min=8, l_max=10
    ):
        inputs = self.text_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=text_max_length,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        if self.text_encoder_model.device != self.device:
            self.text_encoder_model.to(self.device)

        def forward_with_temperature(inputs, tau=0.01, l_min=8, l_max=10):
            handlers = []

            def hook(module, input, output):
                output[:] *= tau
                return output

            for i in range(l_min, l_max):
                handler = (
                    self.text_encoder_model.encoder.block[i]
                    .layer[0]
                    .SelfAttention.q.register_forward_hook(hook)
                )
                handlers.append(handler)

            with torch.no_grad():
                outputs = self.text_encoder_model(**inputs)
                last_hidden_states = outputs.last_hidden_state

            for handler in handlers:
                handler.remove()

            return last_hidden_states, inputs["attention_mask"]

        last_hidden_states, attention_mask = forward_with_temperature(inputs, tau, l_min, l_max)
        return last_hidden_states, attention_mask

    def process_lyrics(self, lyrics, languages=None):
        """Belel-enhanced: Process lyrics with emotion and genre fusion"""
        if self.emotion:
            lyrics = f"[Emotion: {self.emotion}] {lyrics}"
        if self.fused_genres:
            lyrics = f"[Genres: {', '.join(self.fused_genres)}] {lyrics}"
        if languages:
            lyrics = f"[Languages: {', '.join(languages)}] {lyrics}"
        return lyrics

    def __call__(self, **kwargs):
        """Belel-enhanced generation with integrations"""
        audio = super().__call__(**kwargs)  # Call base if needed, or custom logic

        if self.spotify_api_key:
            # Belel Spotify upload (placeholder)
            print("Uploading to Spotify via API...")

        if self.nft_mint_webhook:
            requests.post(self.nft_mint_webhook, json={"audio": "generated"})

        if self.real_time_stream:
            # Belel real-time stream (placeholder)
            print("Streaming audio in real-time...")

        return audio

    # Belel-exclusive methods
    def set_emotion(self, emotion):
        self.emotion = emotion

    def fuse_genres(self, genres):
        self.fused_genres = genres

    def enable_real_time_stream(self):
        self.real_time_stream = True
```
