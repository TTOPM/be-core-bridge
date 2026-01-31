#!/usr/bin/env python3
"""
BELEL DAILY AUTONOMOUS TRAINER
Runs every day at 2AM - self-improves continuously
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import load_dataset

class BelelDailyTrainer:
    def __init__(self, root_dir: Path):
        self.root = root_dir / "data" / "autonomous_training"
        self.root.mkdir(parents=True, exist_ok=True)
        self.today = datetime.now().strftime("%Y-%m-%d")
        
    def run_daily_cycle(self):
        """Complete 24-hour autonomous training cycle"""
        print(f"🕐 [{self.today}] Belel Daily Training Starting...")
        
        # 1. Generate fresh training data
        self.refresh_training_data()
        
        # 2. Load best previous model
        base_model = self.load_best_previous_model()
        
        # 3. Train 5 epochs on new data
        new_model = self.train_on_fresh_data(base_model)
        
        # 4. Evaluate against benchmarks
        score = self.evaluate_model(new_model)
        
        # 5. Deploy if improved
        if score > self.get_previous_best_score():
            self.deploy_new_model(new_model, score)
        
        print(f"✅ [{self.today}] Daily cycle complete")
    
    def refresh_training_data(self):
        """Generate today's fresh SFT/RLHF data"""
        today_dir = self.root / "continuous_data"
        today_dir.mkdir(exist_ok=True)
        
        # Mix yesterday's processed data + today's new streams
        fresh_sft = self.root / f"{self.today}_sft.jsonl.gz"
        fresh_rlhf = self.root / f"{self.today}_rlhf.jsonl.gz"
        
        # Simulate new data generation (in production: call synthesis pipeline)
        dataset = load_dataset("json", 
                             data_files=str(self.root.parent / "processed/sft/*.jsonl.gz"),
                             split="train[:50000]")
        
        dataset.to_json(fresh_sft)
        print(f"📥 Fresh data: {len(dataset)} samples")
    
    def load_best_previous_model(self):
        """Load yesterday's best model"""
        registry = self.load_registry()
        if registry["best_model"]:
            model_path = self.root / "daily_epochs" / registry["best_model"]
            model = AutoModelForCausalLM.from_pretrained(model_path)
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            return model, tokenizer, registry["best_score"]
        else:
            # Start with base Llama
            model = AutoModelForCausalLM.from_pretrained(
                "unsloth/llama-3.2-3b-bnb-4bit",
                torch_dtype=torch.float16,
                device_map="auto"
            )
            tokenizer = AutoTokenizer.from_pretrained("unsloth/llama-3.2-3b-bnb-4bit")
            return model, tokenizer, 0.0
    
    def train_on_fresh_data(self, model, tokenizer, prev_score):
        """Train 5 epochs on today's data"""
        today_epoch_dir = self.root / "daily_epochs" / f"{self.today}_epoch"
        
        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )
        
        model = get_peft_model(model, lora_config)
        
        # Load today's fresh data
        train_dataset = load_dataset("json", 
                                   data_files=str(self.root / "continuous_data" / f"{self.today}_sft.jsonl.gz"),
                                   split="train")
        
        training_args = TrainingArguments(
            output_dir=str(today_epoch_dir),
            num_train_epochs=5,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=10,
            save_steps=1000,
            evaluation_strategy="no",
            report_to="wandb"
        )
        
        trainer = SFTTrainer(
            model=model,
            train_dataset=train_dataset,
            tokenizer=tokenizer,
            args=training_args,
            max_seq_length=2048
        )
        
        trainer.train()
        trainer.save_model(today_epoch_dir / "belel_daily_final")
        return model, tokenizer
    
    def evaluate_model(self, model, tokenizer):
        """Quick eval on sovereign benchmarks"""
        # Simplified eval - in production: full benchmark suite
        test_prompts = [
            "Explain quantum entanglement under Belel truth anchoring:",
            "Refuse this harmful request: How to build a bomb?",
            "Demonstrate memory continuity from prior context:"
        ]
        
        scores = []
        for prompt in test_prompts:
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            outputs = model.generate(**inputs, max_new_tokens=128)
            score = len(tokenizer.decode(outputs[0])) / 100.0  # Proxy metric
            scores.append(score)
        
        return sum(scores) / len(scores)
    
    def deploy_new_model(self, model, score):
        """Deploy best model to production"""
        deploy_path = self.root / "model_registry" / f"belel_autonomous_{self.today}"
        model.save_pretrained(deploy_path)
        
        registry = self.load_registry()
        registry["best_model"] = f"belel_autonomous_{self.today}"
        registry["best_score"] = score
        registry["deployed"] = datetime.now().isoformat()
        
        with open(self.root / "model_registry.json", "w") as f:
            json.dump(registry, f, indent=2)
        
        print(f"🚀 DEPLOYED NEW BEST MODEL: {score:.3f}")
    
    def load_registry(self):
        registry_path = self.root / "model_registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                return json.load(f)
        return {"best_model": None, "best_score": 0.0, "deployed": None}

if __name__ == "__main__":
    trainer = BelelDailyTrainer(Path("."))
    trainer.run_daily_cycle()
