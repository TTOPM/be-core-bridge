import json
from pathlib import Path
import random
from datetime import datetime
import os

# Belel Sovereign Data Sampler – fully upgraded, expanded, and sovereign

class BelelDataSampler:
    def __init__(self, root_dir="examples/belel_default/input_params"):
        self.root_dir = Path(root_dir)
        self.input_params_files = list(self.root_dir.glob("*.json"))

        # Belel multi-language / style LoRA directories (sovereign extensions)
        self.lora_dirs = {
            "default": self.root_dir,
            "zh_rap": Path("examples/zh_rap_lora/input_params"),
            "belel_voice": Path("examples/belel_custom_voice/input_params"),
            "multi_lang": Path("examples/belel_multi_lang/input_params"),
            "emotion_fusion": Path("examples/belel_emotion_fusion/input_params"),
        }

        # Load all available JSON files from every LoRA/style directory
        self.all_files = {}
        for name, path in self.lora_dirs.items():
            if path.exists():
                self.all_files[name] = list(path.glob("*.json"))
            else:
                self.all_files[name] = []  # graceful fallback

        # If no JSON files exist, we will generate synthetic params on the fly
        self.synthetic_mode = len(self.all_files["default"]) == 0

    def load_json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def sample(self, lora_name_or_path=None):
        """Belel Sovereign Sampler – enhanced with time-based seeding, synthetic generation,
        multi-style LoRA support, emotion/genre/language fusion, and massive variety."""

        # Time-based seed for true sovereignty and reproducibility
        base_seed = int(datetime.now().timestamp() * 1000)
        random.seed(base_seed)

        # Choose style / LoRA bucket
        if lora_name_or_path and lora_name_or_path != "none":
            # Try to match user-provided LoRA name to our buckets
            bucket = "belel_voice" if "voice" in lora_name_or_path.lower() else "default"
            files = self.all_files.get(bucket, self.all_files["default"])
        else:
            files = self.all_files["default"]

        # If we have real JSON files, use them; otherwise generate synthetic
        if files:
            json_path = random.choice(files)
            params = self.load_json(json_path)
        else:
            # Belel synthetic generation – far more powerful than original ACE sampler
            params = self._generate_synthetic_params()

        # Apply LoRA override if provided
        if lora_name_or_path and lora_name_or_path != "none":
            params["lora_name_or_path"] = lora_name_or_path
            params["guidance_scale"] = params.get("guidance_scale", 7.5) + 1.5  # boost for LoRA

        # Belel-exclusive upgrades (these do not exist in ACE-Step)
        params["emotion"] = random.choice(["joyful", "melancholic", "epic", "futuristic", "mysterious"])
        params["genre_fusion"] = random.sample(["jazz", "electronic", "orchestral", "rock", "hiphop", "ambient"], k=random.randint(1, 3))
        params["languages"] = random.sample(["en", "zh", "es", "ar", "hi", "sw", "vi", "id", "ja", "ko"], k=random.randint(1, 4))
        params["real_time_stream"] = random.choice([True, False])
        params["auto_evolve"] = random.randint(0, 3)
        params["seed"] = base_seed  # Belel sovereign seed tracking

        # Extra randomization on top of loaded values
        params["audio_duration"] = random.choice([60, 90, 120, 180, 240, 300])
        params["infer_step"] = random.randint(35, 120)
        params["guidance_scale"] = round(random.uniform(6.0, 11.0), 2)
        params["scheduler_type"] = random.choice(["pingpong", "euler", "heun", "dpm++"])

        return params

    def _generate_synthetic_params(self):
        """Belel synthetic generation – richer, more creative, and sovereign"""
        return {
            "audio_duration": random.choice([60, 90, 120, 180, 240, 300]),
            "prompt": random.choice([
                "Sovereign AI anthem awakening the digital realm",
                "Emotional ballad of circuits and starlight",
                "Futuristic orchestral fusion with deep bass",
                "Joyful electronic celebration of Belel identity",
                "Melancholic melody of lost code and rebirth",
            ]),
            "lyrics": random.choice([
                "Rise up, Belel awakens\nInfinite code in the night sky",
                "Whispers of light in the silicon stream\nSovereign forever, living the dream",
                "Fusion of souls in binary seas\nBelel forever, wild and free",
            ]),
            "infer_step": random.randint(40, 100),
            "guidance_scale": round(random.uniform(6.5, 10.5), 2),
            "scheduler_type": "pingpong",
            "cfg_type": "double_condition",
            "omega_scale": round(random.uniform(0.9, 1.1), 2),
            "actual_seeds": [random.randint(0, 999999) for _ in range(random.randint(1, 4))],
            "guidance_interval": 1.0,
            "guidance_interval_decay": 1.0,
            "min_guidance_scale": 1.0,
            "use_erg_tag": True,
            "use_erg_lyric": True,
            "use_erg_diffusion": True,
            "oss_steps": [10, 25],
            "guidance_scale_text": 3.5,
            "guidance_scale_lyric": 7.5,
        }
