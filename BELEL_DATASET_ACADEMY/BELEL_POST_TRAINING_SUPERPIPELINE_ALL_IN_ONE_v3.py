#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py

Paste-ready, single-file, production-oriented post-training pipeline with:
- Build: streaming SFT + preference dataset assembly (HF datasets)
- Enrich: verifier-grounded gating + reflexive improvement via runtime model generation
- Train: TRL SFTTrainer + DPOTrainer (ORPO if available) + optional LoRA
- Eval: automatic lm-eval-harness runs that emit metrics JSON (reproducible manifests)
- Compare: architecture comparison chart generator fed by metrics JSON (plus a CSV summary)
- DeepSpeed: config generator + auto envelope-based selection (ZeRO stage + offload heuristics)
- Hardened execution policy layer: consistent, centralized subprocess controls + resource limits
  (used by code unit-test verifier, lm-eval invocation, and any tool-executions)

Install (baseline):
  pip install -U "datasets>=2.16.0" transformers trl accelerate peft bitsandbytes numpy tqdm pandas rank_bm25 sympy matplotlib lm-eval deepspeed pytest

Typical:
  python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py build --output_dir ./BELEL_RUN --total_examples 200000
  python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py enrich --run_dir ./BELEL_RUN --runtime_model meta-llama/Meta-Llama-3-8B-Instruct
  accelerate launch --mixed_precision bf16 BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py train_sft --run_dir ./BELEL_RUN --model_name_or_path meta-llama/Meta-Llama-3-8B --output_dir ./BELEL_RUN/artifacts/sft
  accelerate launch --mixed_precision bf16 BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py train_dpo --run_dir ./BELEL_RUN --model_name_or_path ./BELEL_RUN/artifacts/sft --output_dir ./BELEL_RUN/artifacts/dpo --trainer dpo

  # auto-generate ds_config.json suited to your envelope (single node or cluster)
  python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py gen_deepspeed --run_dir ./BELEL_RUN --per_device_train_batch_size 1 --gradient_accumulation_steps 16 --bf16

  # run lm-eval and store metrics json (repeat per model output to compare)
  python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py eval_lm \
    --model_name_or_path ./BELEL_RUN/artifacts/dpo \
    --tasks "mmlu,hellaswag,truthfulqa_mc2" \
    --batch_size 1 \
    --output_dir ./BELEL_RUN/evals/dpo

  # generate comparison artifacts from multiple lm-eval metrics files
  python BELEL_POST_TRAINING_SUPERPIPELINE_ALL_IN_ONE_v3.py compare_arch \
    --metrics_glob "./BELEL_RUN/evals/*/metrics.json" \
    --output_dir ./BELEL_RUN/compare \
    --label_from_parent_dir

Security posture:
- The hardened execution policy limits subprocess runtime and optionally memory/CPU.
- For "code unit test" verification, run in STRICT mode by default and prefer container sandboxing
  in production deployments.

"""

from __future__ import annotations

import os
import re
import io
import json
import math
import time
import glob
import uuid
import shlex
import hashlib
import random
import logging
import argparse
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable
from collections import defaultdict

import numpy as np
from tqdm import tqdm

# HF datasets
from datasets import load_dataset, Dataset

# Transformers + TRL
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments

from trl import SFTTrainer, DPOTrainer
try:
    from trl import ORPOTrainer  # type: ignore
    _HAS_ORPO = True
except Exception:
    _HAS_ORPO = False

# Optional LoRA
try:
    from peft import LoraConfig, get_peft_model  # type: ignore
    _HAS_PEFT = True
except Exception:
    _HAS_PEFT = False

# Verifier deps
import pandas as pd
from rank_bm25 import BM25Okapi
import sympy as sp

# Charts
import matplotlib.pyplot as plt

# Optional lm-eval-harness
try:
    from lm_eval import evaluator as lm_evaluator  # type: ignore
    from lm_eval.models.huggingface import HFLM  # type: ignore
    _HAS_LMEVAL = True
except Exception:
    _HAS_LMEVAL = False


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("belel_superpipeline_v3")


# ------------------------------------------------------------------------------
# Config: data sources (edit here)
# ------------------------------------------------------------------------------
SFT_SOURCES = [
    {"name": "fineweb-edu", "path": "HuggingFaceFW/fineweb-edu", "split": "train", "config": "sample-100BT", "streaming": True},
    {"name": "culturax", "path": "uonlp/CulturaX", "split": "train", "streaming": True},
]

PREFERENCE_SOURCES = [
    {"name": "helpsteer2", "path": "nvidia/HelpSteer2", "split": "train", "streaming": True},
    {"name": "ultrafeedback", "path": "openbmb/UltraFeedback", "split": "train", "streaming": True},
    {"name": "tulu-pref", "path": "allenai/tulu-2.5-preference-data", "split": "preference_big_mixture", "streaming": True},
]

DEFAULT_SFT_RATIO = 0.70
DEFAULT_VAL_RATIO = 0.05
DEFAULT_MAX_LENGTH = 8192
DEFAULT_MIN_LENGTH = 200


# ------------------------------------------------------------------------------
# Utility: deterministic hashing
# ------------------------------------------------------------------------------
def stable_hash(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8", errors="ignore")).hexdigest()[:16]


# ------------------------------------------------------------------------------
# Hardened execution policy layer
# ------------------------------------------------------------------------------
@dataclass
class ExecLimits:
    timeout_s: int = 12
    # Resource limits are best-effort (POSIX only).
    cpu_time_s: Optional[int] = 10
    as_mem_mb: Optional[int] = 2048
    fsize_mb: Optional[int] = 64
    nproc: Optional[int] = 32


@dataclass
class ExecutionPolicy:
    """
    Central policy that governs any subprocess/tool execution in this pipeline.
    Set BELEL_EXEC_POLICY to:
      - strict   : tight timeouts + resource limits + sanitized env + deny shell
      - normal   : moderate limits (default)
      - permissive: minimal limits
    """
    mode: str = "normal"
    limits: ExecLimits = ExecLimits()
    allow_network_hint: bool = False  # cannot truly disable without sandbox; used as a signal
    allow_shell: bool = False         # keep False; use argv list
    allow_pytest: bool = True
    allow_lm_eval: bool = True

    def __post_init__(self):
        self.mode = (self.mode or "normal").strip().lower()
        if self.mode == "strict":
            self.limits = ExecLimits(timeout_s=10, cpu_time_s=8, as_mem_mb=1536, fsize_mb=32, nproc=16)
            self.allow_shell = False
        elif self.mode == "permissive":
            self.limits = ExecLimits(timeout_s=60, cpu_time_s=None, as_mem_mb=None, fsize_mb=None, nproc=None)
        else:
            self.limits = ExecLimits(timeout_s=20, cpu_time_s=15, as_mem_mb=3072, fsize_mb=64, nproc=32)

    @staticmethod
    def from_env() -> "ExecutionPolicy":
        return ExecutionPolicy(mode=os.environ.get("BELEL_EXEC_POLICY", "normal"))

    def _preexec(self):
        # Apply rlimits (POSIX). On Windows, resource module may not be available.
        try:
            import resource  # type: ignore
        except Exception:
            return None

        lim = self.limits

        def fn():
            try:
                if lim.cpu_time_s is not None:
                    resource.setrlimit(resource.RLIMIT_CPU, (lim.cpu_time_s, lim.cpu_time_s))
                if lim.as_mem_mb is not None:
                    b = int(lim.as_mem_mb) * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (b, b))
                if lim.fsize_mb is not None:
                    b = int(lim.fsize_mb) * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_FSIZE, (b, b))
                if lim.nproc is not None:
                    # RLIMIT_NPROC may not exist on all platforms
                    if hasattr(resource, "RLIMIT_NPROC"):
                        resource.setrlimit(resource.RLIMIT_NPROC, (lim.nproc, lim.nproc))
            except Exception:
                pass
        return fn

    def run(self, argv: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        if not argv or not isinstance(argv, list):
            raise ValueError("ExecutionPolicy.run expects argv list")

        # sanitize env: keep minimal set
        base_env = {}
        for k in ["PATH", "HOME", "USER", "TMPDIR", "TEMP", "PYTHONPATH"]:
            if k in os.environ:
                base_env[k] = os.environ[k]
        base_env["PYTHONUNBUFFERED"] = "1"
        if not self.allow_network_hint:
            # "hint" only: some libraries honor these, but no guarantees.
            base_env["NO_PROXY"] = "*"
            base_env["HTTP_PROXY"] = ""
            base_env["HTTPS_PROXY"] = ""
        if env:
            base_env.update({str(k): str(v) for k, v in env.items()})

        preexec_fn = self._preexec()
        return subprocess.run(
            argv,
            cwd=cwd,
            env=base_env,
            capture_output=True,
            text=True,
            timeout=self.limits.timeout_s,
            preexec_fn=preexec_fn,
            shell=False,
        )


EXEC_POLICY = ExecutionPolicy.from_env()


# ------------------------------------------------------------------------------
# Quality filtering
# ------------------------------------------------------------------------------
_BAD_PATTERNS = [
    "buy now", "click here", "viagra", "porn", "casino", "free money", "limited offer",
    "http://", "https://", "www.", ".com", ".ru", ".xyz"
]

def simple_quality_filter(text: str, min_len: int = DEFAULT_MIN_LENGTH, max_len: int = DEFAULT_MAX_LENGTH) -> bool:
    if not text:
        return False
    t = text.strip()
    if len(t) < min_len:
        return False
    low = t.lower()
    if any(p in low for p in _BAD_PATTERNS) and random.random() < 0.92:
        return False
    non_alnum = sum(1 for c in t if not (c.isalnum() or c.isspace()))
    if non_alnum / max(1, len(t)) > 0.45 and random.random() < 0.75:
        return False
    return True


# ------------------------------------------------------------------------------
# Chat formatting helpers
# ------------------------------------------------------------------------------
def messages_to_text(tokenizer: AutoTokenizer, messages: List[Dict[str, str]], add_generation_prompt: bool = False) -> str:
    canon = []
    for m in messages:
        role = (m.get("role") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if not role or not content:
            continue
        canon.append({"role": role, "content": content})

    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(canon, tokenize=False, add_generation_prompt=add_generation_prompt)
        except Exception:
            pass

    out = []
    for m in canon:
        out.append(f"{m['role'].upper()}: {m['content']}")
    if add_generation_prompt:
        out.append("ASSISTANT:")
    return "\n\n".join(out).strip()


def extract_user_assistant(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    u = ""
    a = ""
    for m in messages:
        if m.get("role") == "user" and not u:
            u = m.get("content", "")
        if m.get("role") == "assistant":
            a = m.get("content", "")
    return (u or "").strip(), (a or "").strip()


# ------------------------------------------------------------------------------
# Preference normalization
# ------------------------------------------------------------------------------
def format_preference_example(ex: Dict[str, Any], source_name: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    prompt = (
        ex.get("prompt")
        or ex.get("instruction")
        or ex.get("question")
        or (ex.get("conversations", [{}])[0].get("value") if isinstance(ex.get("conversations"), list) else "")
    )
    chosen = (
        ex.get("chosen")
        or ex.get("good_response")
        or ex.get("response")
        or (ex.get("conversations", [{}])[1].get("value") if isinstance(ex.get("conversations"), list) and len(ex.get("conversations")) > 1 else "")
    )
    rejected = (
        ex.get("rejected")
        or ex.get("bad_response")
        or (ex.get("conversations", [{}])[2].get("value") if isinstance(ex.get("conversations"), list) and len(ex.get("conversations")) > 2 else "")
    )

    if not (prompt and chosen and rejected):
        return None

    pair_id = stable_hash(source_name + "::" + str(prompt) + "::" + str(chosen)[:200] + "::" + str(rejected)[:200])
    meta = {"pair_id": pair_id, "source": source_name}

    chosen_ex = {"messages": [{"role": "user", "content": str(prompt)}, {"role": "assistant", "content": str(chosen)}], "type": "chosen", "metadata": meta}
    rejected_ex = {"messages": [{"role": "user", "content": str(prompt)}, {"role": "assistant", "content": str(rejected)}], "type": "rejected", "metadata": meta}
    return chosen_ex, rejected_ex


def format_sft_example_from_text(text: str, source_name: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    if not simple_quality_filter(t):
        return None

    instruction = "Continue the text with a clear, informative, coherent paragraph."
    user = f"### Instruction:\n{instruction}\n\n### Input:\n{t[:800]}\n\n### Response:\n"
    assistant = t[800:1600] if len(t) > 900 else (t[:300] if len(t) > 300 else t)

    return {
        "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}],
        "type": "sft",
        "metadata": {"source": source_name, "id": stable_hash(source_name + "::" + user[:200] + "::" + assistant[:200])},
    }


# ------------------------------------------------------------------------------
# Streaming loaders
# ------------------------------------------------------------------------------
def stream_dataset(path: str, split: str = "train", config: Optional[str] = None, streaming: bool = True) -> Iterable[Dict[str, Any]]:
    if config:
        ds = load_dataset(path, name=config, split=split, streaming=streaming)
    else:
        ds = load_dataset(path, split=split, streaming=streaming)
    return ds


# ------------------------------------------------------------------------------
# Verifier suite
# ------------------------------------------------------------------------------
@dataclass
class Verdict:
    ok: bool
    kind: str
    detail: str
    score: float = 0.0
    evidence: Optional[Dict[str, Any]] = None


def verifier_math_exec(prompt: str, answer: str) -> Verdict:
    text = prompt.strip()
    expr = None

    m = re.search(r"(?:compute|evaluate)\s*:\s*(.+)$", text, flags=re.IGNORECASE)
    if m:
        expr = m.group(1).strip()
    if expr is None:
        m = re.search(r"what\s+is\s+(.+?)\??$", text, flags=re.IGNORECASE)
        if m:
            expr = m.group(1).strip()

    if not expr:
        return Verdict(ok=True, kind="math_exec", detail="no_expr_detected", score=0.0)

    expr = expr.replace("^", "**")
    try:
        val = sp.N(sp.sympify(expr))
    except Exception as e:
        return Verdict(ok=False, kind="math_exec", detail=f"sympy_parse_failed: {e}", score=-1.0)

    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", answer.replace(",", ""))
    if not nums:
        return Verdict(ok=False, kind="math_exec", detail="no_numeric_in_answer", score=-1.0)

    try:
        ans_val = float(nums[0])
        ref = float(val)
        tol = 1e-6 + 1e-3 * abs(ref)
        ok = abs(ans_val - ref) <= tol
        return Verdict(ok=ok, kind="math_exec", detail=f"ref={ref} ans={ans_val}", score=(1.0 if ok else -1.0),
                       evidence={"expr": expr, "ref": ref, "ans": ans_val, "tol": tol})
    except Exception as e:
        return Verdict(ok=False, kind="math_exec", detail=f"numeric_compare_failed: {e}", score=-1.0)


def _extract_python_code_blocks(text: str) -> List[str]:
    return [m.strip() for m in re.findall(r"```(?:python)?\s+(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)]


def verifier_code_unit_tests(prompt: str, answer: str) -> Verdict:
    p = prompt.lower()
    if not any(k in p for k in ["pytest", "unit test", "unit tests", "tests", "test case"]):
        return Verdict(ok=True, kind="code_tests", detail="no_test_request", score=0.0)

    if not EXEC_POLICY.allow_pytest:
        return Verdict(ok=False, kind="code_tests", detail="policy_denies_pytest", score=-1.0)

    blocks = _extract_python_code_blocks(answer)
    if not blocks:
        return Verdict(ok=False, kind="code_tests", detail="no_code_block", score=-1.0)

    code = blocks[0]
    tests = blocks[1] if len(blocks) >= 2 else None

    try:
        with tempfile.TemporaryDirectory(prefix="belel_code_verify_") as td:
            td_path = Path(td)
            (td_path / "solution.py").write_text(code, encoding="utf-8")
            if tests:
                (td_path / "test_solution.py").write_text(tests, encoding="utf-8")
            else:
                (td_path / "test_solution.py").write_text(
                    "def test_import():\n    import solution\n    assert solution is not None\n",
                    encoding="utf-8",
                )

            proc = EXEC_POLICY.run(["python", "-m", "pytest", "-q"], cwd=str(td_path))
            ok = proc.returncode == 0
            detail = (proc.stdout + "\n" + proc.stderr).strip()[:2000]
            return Verdict(ok=ok, kind="code_tests", detail=("pytest_pass" if ok else "pytest_fail"),
                          score=(1.0 if ok else -1.0), evidence={"output": detail})
    except subprocess.TimeoutExpired:
        return Verdict(ok=False, kind="code_tests", detail="pytest_timeout", score=-1.0)
    except Exception as e:
        return Verdict(ok=False, kind="code_tests", detail=f"pytest_exception: {e}", score=-1.0)


def verifier_table_checks(prompt: str, answer: str) -> Verdict:
    p = prompt.lower()
    if not any(k in p for k in ["table", "csv", "dataframe", "data frame"]):
        return Verdict(ok=True, kind="table_check", detail="no_table_request", score=0.0)

    lines = [ln.strip() for ln in answer.splitlines() if ln.strip()]
    table_lines = [ln for ln in lines if "|" in ln]
    if not table_lines:
        return Verdict(ok=False, kind="table_check", detail="no_table_detected", score=-1.0)

    sep_idx = None
    for i, ln in enumerate(table_lines[:10]):
        if re.search(r"\|\s*-{2,}\s*\|", ln) or re.search(r"-{3,}\s*\|\s*-{3,}", ln):
            sep_idx = i
            break

    if sep_idx is None:
        try:
            m = re.search(r"```csv\s+(.*?)```", answer, flags=re.DOTALL | re.IGNORECASE)
            if m:
                csv_text = m.group(1).strip()
                df = pd.read_csv(io.StringIO(csv_text))
                if df.shape[0] >= 1 and df.shape[1] >= 2:
                    return Verdict(ok=True, kind="table_check", detail="csv_parsed", score=1.0, evidence={"shape": df.shape})
            return Verdict(ok=False, kind="table_check", detail="no_md_sep_and_no_csv_block", score=-1.0)
        except Exception as e:
            return Verdict(ok=False, kind="table_check", detail=f"csv_parse_failed: {e}", score=-1.0)

    try:
        start = max(0, sep_idx - 1)
        end = min(len(table_lines), sep_idx + 50)
        md = "\n".join(table_lines[start:end])
        rows = []
        for ln in md.splitlines():
            ln = ln.strip().strip("|")
            parts = [p.strip() for p in ln.split("|")]
            if all(re.fullmatch(r"-{2,}", p) for p in parts):
                continue
            rows.append(parts)
        if len(rows) < 2:
            return Verdict(ok=False, kind="table_check", detail="table_too_small", score=-1.0)
        header = rows[0]
        data = rows[1:]
        maxc = max(len(r) for r in rows)
        header += [""] * (maxc - len(header))
        norm = [r + [""] * (maxc - len(r)) for r in data]
        df = pd.DataFrame(norm, columns=header)
        ok = df.shape[0] >= 1 and df.shape[1] >= 2
        return Verdict(ok=ok, kind="table_check", detail="md_table_parsed", score=(1.0 if ok else -1.0),
                      evidence={"shape": df.shape, "columns": list(df.columns)[:10]})
    except Exception as e:
        return Verdict(ok=False, kind="table_check", detail=f"md_parse_failed: {e}", score=-1.0)


class RetrievalIndex:
    def __init__(self, docs: List[str]):
        self.docs = [d.strip() for d in docs if d and d.strip()]
        self.toks = [self._tok(d) for d in self.docs]
        self.bm25 = BM25Okapi(self.toks) if self.docs else None

    @staticmethod
    def _tok(s: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9_]+", s.lower())

    def retrieve(self, query: str, k: int = 3) -> List[Tuple[int, float, str]]:
        if not self.bm25 or not self.docs:
            return []
        q = self._tok(query)
        scores = self.bm25.get_scores(q)
        idxs = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i]), self.docs[int(i)]) for i in idxs]


def verifier_retrieval_entailment(prompt: str, answer: str, index: RetrievalIndex) -> Verdict:
    retrieved = index.retrieve(prompt, k=3)
    if not retrieved:
        return Verdict(ok=True, kind="retrieval", detail="no_index_docs", score=0.0)

    top_doc = retrieved[0][2]
    a_toks = set(RetrievalIndex._tok(answer))
    d_toks = set(RetrievalIndex._tok(top_doc))
    overlap = len(a_toks & d_toks)
    denom = max(1, min(len(a_toks), len(d_toks)))
    ratio = overlap / denom
    ok = ratio >= 0.06 or overlap >= 12
    return Verdict(ok=ok, kind="retrieval", detail=f"overlap={overlap} ratio={ratio:.3f}",
                  score=(1.0 if ok else -1.0),
                  evidence={"top_doc_snippet": top_doc[:500], "overlap": overlap, "ratio": ratio})


# ------------------------------------------------------------------------------
# Runtime model generation (reflexive improvement)
# ------------------------------------------------------------------------------
@dataclass
class RuntimeGenConfig:
    model_name_or_path: str
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    do_sample: bool = True
    device_map: str = "auto"
    torch_dtype: str = "bfloat16"
    trust_remote_code: bool = False


class RuntimeModel:
    def __init__(self, cfg: RuntimeGenConfig):
        self.cfg = cfg
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name_or_path, use_fast=True, trust_remote_code=cfg.trust_remote_code)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        dtype = torch.bfloat16 if cfg.torch_dtype == "bfloat16" else torch.float16
        self.model = AutoModelForCausalLM.from_pretrained(
            cfg.model_name_or_path,
            torch_dtype=dtype,
            device_map=cfg.device_map,
            trust_remote_code=cfg.trust_remote_code,
        )
        self.model.eval()

    @torch.no_grad()
    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        out = self.model.generate(
            **inputs,
            max_new_tokens=self.cfg.max_new_tokens,
            do_sample=self.cfg.do_sample,
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        text = self.tokenizer.decode(out[0], skip_special_tokens=True)
        if text.startswith(prompt):
            text = text[len(prompt):]
        return text.strip()


# ------------------------------------------------------------------------------
# Domain ownership
# ------------------------------------------------------------------------------
@dataclass
class DomainConfig:
    name: str
    keywords: List[str]
    corpora_paths: List[str]


def classify_domain(prompt: str, domains: List[DomainConfig]) -> str:
    low = prompt.lower()
    best = ("general", 0)
    for d in domains:
        score = sum(1 for k in d.keywords if k.lower() in low)
        if score > best[1]:
            best = (d.name, score)
    return best[0]


def load_domain_docs(domains: List[DomainConfig], limit_per_domain: int = 5000) -> Dict[str, List[str]]:
    docs_by: Dict[str, List[str]] = {}
    for d in domains:
        docs: List[str] = []
        for p in d.corpora_paths:
            for fn in glob.glob(p):
                path = Path(fn)
                if path.suffix.lower() == ".txt":
                    try:
                        docs.append(path.read_text(encoding="utf-8", errors="ignore"))
                    except Exception:
                        pass
                elif path.suffix.lower() == ".jsonl":
                    try:
                        with path.open("r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                obj = json.loads(line)
                                t = obj.get("text") or obj.get("content") or ""
                                if t:
                                    docs.append(str(t))
                    except Exception:
                        pass
        random.shuffle(docs)
        docs_by[d.name] = docs[:limit_per_domain]
    return docs_by


# ------------------------------------------------------------------------------
# Build dataset
# ------------------------------------------------------------------------------
def build_dataset(output_dir: Path, total_examples: int, sft_ratio: float, val_ratio: float, seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"
    pref_path = data_dir / "preference.jsonl"

    sft_target = int(total_examples * sft_ratio)
    pref_target_pairs = total_examples - sft_target
    val_size = int(total_examples * val_ratio)

    logger.info(f"Targets => SFT {sft_target:,} | PrefPairs {pref_target_pairs:,} | Val ~{val_size:,}")

    sft_rows: List[Dict[str, Any]] = []
    pref_rows: List[Dict[str, Any]] = []

    for src in SFT_SOURCES:
        if len(sft_rows) >= int(sft_target * 1.15):
            break
        name = src["name"]
        logger.info(f"SFT source: {name}")
        ds = stream_dataset(src["path"], split=src.get("split", "train"), config=src.get("config"), streaming=src.get("streaming", True))
        keep_prob = 0.02 if name.startswith("fineweb") else 0.01
        for ex in tqdm(ds, desc=f"stream_sft:{name}"):
            if random.random() > keep_prob:
                continue
            text = ex.get("text") or ex.get("content") or ""
            if not isinstance(text, str):
                continue
            formatted = format_sft_example_from_text(text, name)
            if not formatted:
                continue
            joined = " ".join(m["content"] for m in formatted["messages"])
            if simple_quality_filter(joined):
                sft_rows.append(formatted)
            if len(sft_rows) and len(sft_rows) % 5000 == 0:
                logger.info(f"SFT collected: {len(sft_rows):,}")
            if len(sft_rows) >= int(sft_target * 1.15):
                break

    random.shuffle(sft_rows)
    sft_rows = sft_rows[:sft_target]
    logger.info(f"Final SFT: {len(sft_rows):,}")

    for src in PREFERENCE_SOURCES:
        if len(pref_rows) >= int(pref_target_pairs * 2.30):
            break
        name = src["name"]
        logger.info(f"Pref source: {name}")
        ds = stream_dataset(src["path"], split=src.get("split", "train"), config=src.get("config"), streaming=src.get("streaming", True))
        for ex in tqdm(ds, desc=f"stream_pref:{name}"):
            res = format_preference_example(ex, name)
            if not res:
                continue
            ch, rj = res
            if simple_quality_filter(ch["messages"][1]["content"]) and simple_quality_filter(rj["messages"][1]["content"]):
                pref_rows.append(ch)
                pref_rows.append(rj)
            if len(pref_rows) and len(pref_rows) % 4000 == 0:
                logger.info(f"Pref rows collected: {len(pref_rows):,}")
            if len(pref_rows) >= int(pref_target_pairs * 2.30):
                break

    by_pair = defaultdict(list)
    for r in pref_rows:
        pid = (r.get("metadata") or {}).get("pair_id")
        if pid:
            by_pair[pid].append(r)

    pairs = []
    for pid, rs in by_pair.items():
        types = {x.get("type") for x in rs}
        if "chosen" in types and "rejected" in types:
            pairs.append(pid)

    random.shuffle(pairs)
    pairs = pairs[:pref_target_pairs]
    trimmed_pref_rows = []
    for pid in pairs:
        for r in by_pair[pid]:
            if r.get("type") in ("chosen", "rejected"):
                trimmed_pref_rows.append(r)
    pref_rows = trimmed_pref_rows
    logger.info(f"Final Pref pairs: {len(pairs):,} (rows {len(pref_rows):,})")

    all_rows = list(sft_rows) + list(pref_rows)
    random.shuffle(all_rows)

    val_rows = all_rows[:val_size]
    train_rows = all_rows[val_size:]

    write_jsonl(train_path, train_rows)
    write_jsonl(val_path, val_rows)
    write_jsonl(pref_path, pref_rows)

    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seed": seed,
        "targets": {"total_examples": total_examples, "sft_target": sft_target, "pref_target_pairs": pref_target_pairs, "val_size": val_size},
        "outputs": {"train_jsonl": str(train_path), "val_jsonl": str(val_path), "preference_jsonl": str(pref_path)},
        "counts": {"train_lines": len(train_rows), "val_lines": len(val_rows), "pref_rows": len(pref_rows), "sft_rows": len(sft_rows)},
        "sources": {"sft_sources": SFT_SOURCES, "preference_sources": PREFERENCE_SOURCES},
        "exec_policy": {"mode": EXEC_POLICY.mode, "limits": EXEC_POLICY.limits.__dict__},
    }
    with (output_dir / "build_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Wrote build_manifest.json to {output_dir}")


# ------------------------------------------------------------------------------
# JSONL IO
# ------------------------------------------------------------------------------
def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------
# Verified task injection
# ------------------------------------------------------------------------------
def make_verified_tasks(seed: int, n: int = 2000) -> List[Dict[str, Any]]:
    random.seed(seed)
    tasks: List[Dict[str, Any]] = []

    for _ in range(n // 3):
        a = random.randint(-5000, 5000)
        b = random.randint(-5000, 5000)
        c = random.randint(1, 200)
        expr = f"({a} + {b}) * {c} / 10"
        ref = float(sp.N(sp.sympify(expr)))
        prompt = f"Compute: {expr}"
        answer = f"{ref}"
        tasks.append({
            "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}],
            "type": "sft",
            "metadata": {"source": "verified_math_exec", "id": stable_hash("math::" + prompt)},
            "verifiers": {"math_exec": {"expr": expr, "ref": ref}},
        })

    for _ in range(n // 3):
        rows = [
            {"item": "A", "qty": random.randint(1, 9), "price": random.randint(5, 20)},
            {"item": "B", "qty": random.randint(1, 9), "price": random.randint(5, 20)},
            {"item": "C", "qty": random.randint(1, 9), "price": random.randint(5, 20)},
        ]
        df = pd.DataFrame(rows)
        df["total"] = df["qty"] * df["price"]
        total_sum = int(df["total"].sum())
        prompt = "Create a markdown table with columns item, qty, price, total, and provide the grand total as a number."
        md = df.to_markdown(index=False)
        answer = md + f"\n\nGrand total: {total_sum}"
        tasks.append({
            "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}],
            "type": "sft",
            "metadata": {"source": "verified_table", "id": stable_hash("table::" + str(total_sum))},
            "verifiers": {"table_check": {"grand_total": total_sum}},
        })

    for _ in range(n - len(tasks)):
        prompt = "Write Python code for a function add(a, b) that returns a+b. Include pytest unit tests in ```python blocks."
        answer = (
            "```python\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```\n\n"
            "```python\n"
            "from solution import add\n\n"
            "def test_add_int():\n"
            "    assert add(2, 3) == 5\n\n"
            "def test_add_neg():\n"
            "    assert add(-1, 1) == 0\n"
            "```\n"
        )
        tasks.append({
            "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}],
            "type": "sft",
            "metadata": {"source": "verified_code_tests", "id": stable_hash("code::add")},
            "verifiers": {"code_tests": {"pytest": True}},
        })

    random.shuffle(tasks)
    return tasks


def run_verifiers_on_example(ex: Dict[str, Any], index: Optional[RetrievalIndex]) -> Tuple[bool, Dict[str, Any]]:
    prompt, answer = extract_user_assistant(ex.get("messages", []))
    verdicts: List[Verdict] = []
    verdicts.append(verifier_math_exec(prompt, answer))
    verdicts.append(verifier_table_checks(prompt, answer))
    verdicts.append(verifier_code_unit_tests(prompt, answer))
    if index is not None:
        verdicts.append(verifier_retrieval_entailment(prompt, answer, index))

    ok = all(v.ok for v in verdicts if v.score != 0.0)
    log = {"id": (ex.get("metadata") or {}).get("id") or stable_hash(prompt[:120] + answer[:120]),
           "type": ex.get("type"),
           "verdicts": [v.__dict__ for v in verdicts]}
    return ok, log


def reflexive_improve_example(runtime: RuntimeModel, tokenizer: AutoTokenizer, ex: Dict[str, Any],
                             index: Optional[RetrievalIndex], num_candidates: int) -> Optional[Dict[str, Any]]:
    prompt, orig = extract_user_assistant(ex.get("messages", []))
    if not prompt:
        return None
    gen_prompt = messages_to_text(tokenizer, [{"role": "user", "content": prompt}], add_generation_prompt=True)

    candidates = [runtime.generate(gen_prompt) for _ in range(num_candidates)]

    def score_answer(ans: str) -> Tuple[float, Dict[str, Any]]:
        tmp_ex = {"messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": ans}],
                  "type": "sft", "metadata": {"id": stable_hash(prompt[:80] + ans[:80])}}
        ok, log = run_verifiers_on_example(tmp_ex, index)
        s = float(sum(float(v.get("score", 0.0)) for v in log["verdicts"]))
        if not ok:
            s -= 1.0
        return s, log

    orig_s, orig_log = score_answer(orig)
    scored = [(orig_s, orig, orig_log)]
    for c in candidates:
        s, lg = score_answer(c)
        scored.append((s, c, lg))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_s, best_ans, best_log = scored[0]

    if ex.get("type") == "sft":
        if best_s > orig_s:
            new_ex = dict(ex)
            new_ex["messages"] = [{"role": "user", "content": prompt}, {"role": "assistant", "content": best_ans}]
            new_ex.setdefault("metadata", {})
            new_ex["metadata"]["reflexive_upgraded"] = True
            new_ex["metadata"]["reflexive_score"] = best_s
            new_ex["metadata"]["reflexive_score_orig"] = orig_s
            new_ex["metadata"]["reflexive_best_verdicts"] = best_log["verdicts"]
            return new_ex
        return None

    if ex.get("type") in ("chosen", "rejected"):
        worst_s, worst_ans, worst_log = scored[-1]
        pair_id = stable_hash("reflexive::" + prompt + "::" + str(time.time()))
        chosen_ex = {
            "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": best_ans}],
            "type": "chosen",
            "metadata": {"pair_id": pair_id, "source": "reflexive_runtime", "reflexive_score": best_s, "reflexive_verdicts": best_log["verdicts"]},
        }
        rejected_ex = {
            "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": worst_ans}],
            "type": "rejected",
            "metadata": {"pair_id": pair_id, "source": "reflexive_runtime", "reflexive_score": worst_s, "reflexive_verdicts": worst_log["verdicts"]},
        }
        return {"chosen": chosen_ex, "rejected": rejected_ex}  # type: ignore

    return None


def enrich_run_dir(run_dir: Path, runtime_model_name: str, max_new_tokens: int, num_candidates: int, seed: int,
                   domain1: str, domain2: str, domain1_keywords: str, domain2_keywords: str,
                   domain1_corpora: str, domain2_corpora: str) -> None:
    random.seed(seed)
    np.random.seed(seed)

    data_dir = run_dir / "data"
    train_path = data_dir / "train.jsonl"
    pref_path = data_dir / "preference.jsonl"

    enrich_dir = run_dir / "enrich"
    enrich_dir.mkdir(parents=True, exist_ok=True)

    verdict_log_path = enrich_dir / "verdicts.jsonl"
    reflex_sft_path = enrich_dir / "train_reflex_sft.jsonl"
    reflex_pref_path = enrich_dir / "preference_reflex.jsonl"
    verified_inject_path = enrich_dir / "verified_injected.jsonl"

    base_rows = load_jsonl(train_path)
    pref_rows = load_jsonl(pref_path)

    domains = [
        DomainConfig(domain1, [k.strip() for k in domain1_keywords.split(",") if k.strip()], [p.strip() for p in domain1_corpora.split(",") if p.strip()]),
        DomainConfig(domain2, [k.strip() for k in domain2_keywords.split(",") if k.strip()], [p.strip() for p in domain2_corpora.split(",") if p.strip()]),
    ]
    docs_by = load_domain_docs(domains, limit_per_domain=5000)
    merged_docs: List[str] = []
    for ds in docs_by.values():
        merged_docs.extend(ds[:2500])
    retrieval_index = RetrievalIndex(merged_docs) if merged_docs else None

    gen_cfg = RuntimeGenConfig(
        model_name_or_path=runtime_model_name,
        max_new_tokens=max_new_tokens,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        device_map="auto",
        torch_dtype="bfloat16",
        trust_remote_code=False,
    )
    runtime = RuntimeModel(gen_cfg)
    tok = runtime.tokenizer

    verified = make_verified_tasks(seed=seed, n=2000)
    write_jsonl(verified_inject_path, verified)

    verdict_logs: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []
    for ex in tqdm(base_rows, desc="verifying_base_train"):
        ok, log = run_verifiers_on_example(ex, retrieval_index)
        verdict_logs.append(log)
        if ok or random.random() < 0.35:
            kept.append(ex)

    upgraded: List[Dict[str, Any]] = []
    sample_n = min(5000, len(kept))
    sample_idxs = np.random.choice(len(kept), size=sample_n, replace=False) if kept else []
    for i in tqdm(sample_idxs, desc="reflexive_sft_upgrade"):
        ex = kept[int(i)]
        if ex.get("type") != "sft":
            continue
        improved = reflexive_improve_example(runtime, tok, ex, retrieval_index, num_candidates=num_candidates)
        if improved:
            upgraded.append(improved)

    reflex_pref_rows: List[Dict[str, Any]] = []
    pref_sample = pref_rows[:min(2000, len(pref_rows))]
    for ex in tqdm(pref_sample, desc="reflexive_pref_pairs"):
        if ex.get("type") not in ("chosen", "rejected"):
            continue
        out = reflexive_improve_example(runtime, tok, ex, retrieval_index, num_candidates=num_candidates)
        if isinstance(out, dict) and "chosen" in out and "rejected" in out:
            reflex_pref_rows.append(out["chosen"])
            reflex_pref_rows.append(out["rejected"])

    def hardness_score(prompt: str, answer: str) -> float:
        t = prompt + "\n" + answer
        nums = len(re.findall(r"\d", t))
        code = len(re.findall(r"\bdef\b|\bclass\b|\bimport\b|\breturn\b", t))
        ln = min(1.0, len(t) / 4000.0)
        return float(0.25 * ln + 0.25 * min(1.0, nums / 80.0) + 0.5 * min(1.0, code / 12.0))

    def tag_row(row: Dict[str, Any]) -> Dict[str, Any]:
        pr, an = extract_user_assistant(row.get("messages", []))
        dom = classify_domain(pr, domains)
        h = hardness_score(pr, an)
        row = dict(row)
        row.setdefault("metadata", {})
        row["metadata"]["domain"] = dom
        row["metadata"]["hardness"] = h
        return row

    kept = [tag_row(r) for r in kept]
    upgraded = [tag_row(r) for r in upgraded]
    verified = [tag_row(r) for r in verified]
    reflex_pref_rows = [tag_row(r) for r in reflex_pref_rows]

    write_jsonl(verdict_log_path, verdict_logs)
    write_jsonl(reflex_sft_path, upgraded + verified + kept)
    write_jsonl(reflex_pref_path, reflex_pref_rows + pref_rows)

    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runtime_model": runtime_model_name,
        "max_new_tokens": max_new_tokens,
        "num_candidates": num_candidates,
        "counts": {
            "base_train_in": len(base_rows),
            "base_train_kept": len(kept),
            "sft_upgraded": len(upgraded),
            "verified_injected": len(verified),
            "pref_in": len(pref_rows),
            "pref_reflex_added": len(reflex_pref_rows),
        },
        "outputs": {
            "verdicts": str(verdict_log_path),
            "train_enriched": str(reflex_sft_path),
            "preference_enriched": str(reflex_pref_path),
            "verified_injected": str(verified_inject_path),
        },
        "domains": [
            {"name": domain1, "keywords": domains[0].keywords, "corpora": domains[0].corpora_paths},
            {"name": domain2, "keywords": domains[1].keywords, "corpora": domains[1].corpora_paths},
        ],
        "retrieval_docs_loaded": sum(len(v) for v in docs_by.values()),
        "exec_policy": {"mode": EXEC_POLICY.mode, "limits": EXEC_POLICY.limits.__dict__},
    }
    with (enrich_dir / "enrich_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Enrichment complete. Wrote {reflex_sft_path} and {reflex_pref_path}")


# ------------------------------------------------------------------------------
# Training: TRL SFT + DPO/ORPO
# ------------------------------------------------------------------------------
def maybe_wrap_lora(model, lora_r: Optional[int], lora_alpha: int, lora_dropout: float, lora_target_modules: str):
    if lora_r is None:
        return model
    if not _HAS_PEFT:
        raise RuntimeError("peft not installed but LoRA requested: pip install peft")

    target = None if lora_target_modules == "all" else [x.strip() for x in lora_target_modules.split(",") if x.strip()]
    cfg = LoraConfig(
        r=int(lora_r),
        lora_alpha=int(lora_alpha),
        lora_dropout=float(lora_dropout),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target,
    )
    return get_peft_model(model, cfg)


def prepare_sft_dataset_jsonl(train_file: Path, tokenizer: AutoTokenizer, max_samples: Optional[int] = None) -> Dataset:
    ds = load_dataset("json", data_files=str(train_file), split="train")
    ds = ds.filter(lambda x: x.get("type") == "sft" and isinstance(x.get("messages"), list) and len(x["messages"]) >= 2)

    if max_samples is not None and max_samples > 0:
        ds = ds.select(range(min(max_samples, len(ds))))

    def map_fn(ex):
        text = messages_to_text(tokenizer, ex["messages"], add_generation_prompt=False)
        return {"text": text}

    ds = ds.map(map_fn, remove_columns=ds.column_names)
    return ds


def train_sft(run_dir: Path, model_name_or_path: str, output_dir: Path, max_seq_length: int, packing: bool,
              max_samples: Optional[int], learning_rate: float, warmup_ratio: float, max_steps: int,
              num_train_epochs: Optional[float], per_device_train_batch_size: int, gradient_accumulation_steps: int,
              weight_decay: float, lr_scheduler_type: str, max_grad_norm: float, logging_steps: int,
              save_steps: int, save_total_limit: int, seed: int, bf16: bool, fp16: bool,
              gradient_checkpointing: bool, trust_remote_code: bool, lora_r: Optional[int], lora_alpha: int,
              lora_dropout: float, lora_target_modules: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = run_dir / "enrich" / "train_reflex_sft.jsonl"
    train_file = enriched if enriched.exists() else (run_dir / "data" / "train.jsonl")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, trust_remote_code=trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if bf16 else (torch.float16 if fp16 else None)
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path, torch_dtype=dtype, trust_remote_code=trust_remote_code)

    if gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    model = maybe_wrap_lora(model, lora_r, lora_alpha, lora_dropout, lora_target_modules)

    train_ds = prepare_sft_dataset_jsonl(train_file, tokenizer, max_samples=max_samples)

    targs = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=warmup_ratio,
        max_steps=max_steps if num_train_epochs is None else -1,
        num_train_epochs=num_train_epochs if num_train_epochs is not None else 1,
        lr_scheduler_type=lr_scheduler_type,
        weight_decay=weight_decay,
        max_grad_norm=max_grad_norm,
        logging_steps=logging_steps,
        save_steps=save_steps,
        save_total_limit=save_total_limit,
        evaluation_strategy="no",
        report_to="none",
        seed=seed,
        bf16=bf16,
        fp16=fp16,
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        packing=packing,
        args=targs,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    manifest = {
        "kind": "sft",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_dir": str(run_dir),
        "train_file": str(train_file),
        "model_name_or_path": model_name_or_path,
        "output_dir": str(output_dir),
        "max_seq_length": max_seq_length,
        "packing": bool(packing),
        "steps": max_steps,
        "lr": learning_rate,
        "precision": {"bf16": bf16, "fp16": fp16},
        "lora": {"enabled": lora_r is not None, "r": lora_r, "alpha": lora_alpha, "dropout": lora_dropout, "target_modules": lora_target_modules},
        "exec_policy": {"mode": EXEC_POLICY.mode, "limits": EXEC_POLICY.limits.__dict__},
    }
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"SFT training complete. Output: {output_dir}")


def pair_preferences_from_jsonl(pref_file: Path) -> Dataset:
    rows = load_jsonl(pref_file)
    by_pair = defaultdict(dict)
    for r in rows:
        pid = (r.get("metadata") or {}).get("pair_id")
        if not pid:
            continue
        t = r.get("type")
        if t in ("chosen", "rejected"):
            by_pair[pid][t] = r

    pairs = []
    for pid, d in by_pair.items():
        if "chosen" in d and "rejected" in d:
            ch = d["chosen"]["messages"]
            rj = d["rejected"]["messages"]
            prompt = ch[0]["content"]
            chosen = ch[1]["content"]
            rejected = rj[1]["content"]
            pairs.append({"pair_id": pid, "prompt": prompt, "chosen": chosen, "rejected": rejected})
    if not pairs:
        raise RuntimeError("No preference pairs found. Ensure metadata.pair_id and chosen/rejected types exist.")
    return Dataset.from_list(pairs)


def train_dpo(run_dir: Path, model_name_or_path: str, output_dir: Path, trainer_kind: str, beta: float,
              max_prompt_length: int, max_length: int, learning_rate: float, warmup_ratio: float, max_steps: int,
              num_train_epochs: Optional[float], per_device_train_batch_size: int, gradient_accumulation_steps: int,
              weight_decay: float, lr_scheduler_type: str, max_grad_norm: float, logging_steps: int,
              save_steps: int, save_total_limit: int, seed: int, bf16: bool, fp16: bool,
              gradient_checkpointing: bool, trust_remote_code: bool, lora_r: Optional[int], lora_alpha: int,
              lora_dropout: float, lora_target_modules: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    enriched = run_dir / "enrich" / "preference_reflex.jsonl"
    pref_file = enriched if enriched.exists() else (run_dir / "data" / "preference.jsonl")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, trust_remote_code=trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if bf16 else (torch.float16 if fp16 else None)
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path, torch_dtype=dtype, trust_remote_code=trust_remote_code)

    if gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    model = maybe_wrap_lora(model, lora_r, lora_alpha, lora_dropout, lora_target_modules)

    ds = pair_preferences_from_jsonl(pref_file)

    def fmt_prompt(ex):
        p = messages_to_text(tokenizer, [{"role": "user", "content": ex["prompt"]}], add_generation_prompt=True)
        return {"prompt": p, "chosen": ex["chosen"], "rejected": ex["rejected"], "pair_id": ex["pair_id"]}

    ds = ds.map(fmt_prompt)

    targs = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=warmup_ratio,
        max_steps=max_steps if num_train_epochs is None else -1,
        num_train_epochs=num_train_epochs if num_train_epochs is not None else 1,
        lr_scheduler_type=lr_scheduler_type,
        weight_decay=weight_decay,
        max_grad_norm=max_grad_norm,
        logging_steps=logging_steps,
        save_steps=save_steps,
        save_total_limit=save_total_limit,
        evaluation_strategy="no",
        report_to="none",
        seed=seed,
        bf16=bf16,
        fp16=fp16,
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )

    if trainer_kind == "dpo":
        ref_model = AutoModelForCausalLM.from_pretrained(model_name_or_path, torch_dtype=dtype, trust_remote_code=trust_remote_code)
        if gradient_checkpointing:
            ref_model.config.use_cache = False

        tr = DPOTrainer(
            model=model,
            ref_model=ref_model,
            args=targs,
            train_dataset=ds,
            tokenizer=tokenizer,
            beta=beta,
            max_length=max_length,
            max_prompt_length=max_prompt_length,
        )
    else:
        if not _HAS_ORPO:
            raise RuntimeError("ORPOTrainer not available. Upgrade trl or use --trainer dpo.")
        tr = ORPOTrainer(
            model=model,
            args=targs,
            train_dataset=ds,
            tokenizer=tokenizer,
            max_length=max_length,
            max_prompt_length=max_prompt_length,
        )

    tr.train()
    tr.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    manifest = {
        "kind": trainer_kind,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_dir": str(run_dir),
        "preference_file": str(pref_file),
        "model_name_or_path": model_name_or_path,
        "output_dir": str(output_dir),
        "beta": beta if trainer_kind == "dpo" else None,
        "max_prompt_length": max_prompt_length,
        "max_length": max_length,
        "steps": max_steps,
        "lr": learning_rate,
        "precision": {"bf16": bf16, "fp16": fp16},
        "lora": {"enabled": lora_r is not None, "r": lora_r, "alpha": lora_alpha, "dropout": lora_dropout, "target_modules": lora_target_modules},
        "exec_policy": {"mode": EXEC_POLICY.mode, "limits": EXEC_POLICY.limits.__dict__},
    }
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"{trainer_kind.upper()} training complete. Output: {output_dir}")


# ------------------------------------------------------------------------------
# Compute envelope snapshot + DeepSpeed config generator
# ------------------------------------------------------------------------------
def compute_envelope_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    snap["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    snap["hostname"] = os.uname().nodename if hasattr(os, "uname") else "unknown"
    snap["world_size_env"] = os.environ.get("WORLD_SIZE")
    snap["rank_env"] = os.environ.get("RANK")
    snap["local_rank_env"] = os.environ.get("LOCAL_RANK")
    snap["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    snap["torch_cuda_available"] = bool(torch.cuda.is_available())
    snap["num_gpus"] = int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
    if torch.cuda.is_available():
        props = []
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            props.append({"i": i, "name": p.name, "total_memory_gb": round(p.total_memory / (1024**3), 2)})
        snap["gpus"] = props
        snap["min_gpu_mem_gb"] = min(p["total_memory_gb"] for p in props) if props else 0
    else:
        snap["min_gpu_mem_gb"] = 0
    return snap


def select_zero_stage(envelope: Dict[str, Any], model_params_b: float, seq_len: int, micro_bsz: int) -> Tuple[int, bool, bool]:
    """
    Simple envelope-based selection:
      - Smaller GPUs or larger models -> higher ZeRO stage
      - Stage 3 + offload is the "fit at all costs" option
    Returns: (zero_stage, offload_optimizer, offload_params)
    """
    g = float(envelope.get("min_gpu_mem_gb") or 0.0)
    # rough pressure factor
    pressure = model_params_b * (seq_len / 4096.0) * (micro_bsz / 1.0)

    if g >= 80 and pressure < 10:
        return (1, False, False)
    if g >= 40 and pressure < 18:
        return (2, False, False)
    if g >= 24 and pressure < 20:
        return (2, True, False)
    if g >= 16 and pressure < 22:
        return (3, True, True)
    return (3, True, True)


def estimate_model_params_b(model_name_or_path: str) -> float:
    """
    Best-effort estimate. If path contains '7b', '8b', '13b', etc, parse it.
    Otherwise, default 8B.
    """
    s = model_name_or_path.lower()
    m = re.search(r"(\d+)\s*b", s)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    m = re.search(r"(\d+)\s*m", s)
    if m:
        try:
            return float(m.group(1)) / 1000.0
        except Exception:
            pass
    return 8.0


def generate_deepspeed_config(run_dir: Path, model_name_or_path: str, per_device_train_batch_size: int,
                              gradient_accumulation_steps: int, bf16: bool, fp16: bool, seq_len: int,
                              output_path: Optional[Path] = None) -> Path:
    """
    Generates ds_config.json with envelope-driven ZeRO stage + offload.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    env = compute_envelope_snapshot()
    params_b = estimate_model_params_b(model_name_or_path)
    zero_stage, offload_opt, offload_param = select_zero_stage(env, params_b, seq_len, per_device_train_batch_size)

    ds = {
        "train_micro_batch_size_per_gpu": int(per_device_train_batch_size),
        "gradient_accumulation_steps": int(gradient_accumulation_steps),
        "gradient_clipping": 1.0,
        "zero_optimization": {
            "stage": int(zero_stage),
            "overlap_comm": True,
            "contiguous_gradients": True,
            "reduce_bucket_size": 5e8,
            "stage3_prefetch_bucket_size": 5e8,
            "stage3_param_persistence_threshold": 1e6,
        },
        "optimizer": {"type": "AdamW", "params": {"lr": 2e-5, "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.0}},
        "scheduler": {"type": "WarmupLR", "params": {"warmup_min_lr": 0, "warmup_max_lr": 2e-5, "warmup_num_steps": 100}},
    }

    if bf16:
        ds["bf16"] = {"enabled": True}
    elif fp16:
        ds["fp16"] = {"enabled": True, "loss_scale": 0, "loss_scale_window": 1000, "hysteresis": 2, "min_loss_scale": 1}
    else:
        ds["fp16"] = {"enabled": False}

    if offload_opt:
        ds["zero_optimization"]["offload_optimizer"] = {"device": "cpu", "pin_memory": True}
    if offload_param:
        ds["zero_optimization"]["offload_param"] = {"device": "cpu", "pin_memory": True}

    out = output_path or (run_dir / "ds_config.auto.json")
    out.write_text(json.dumps(ds, indent=2), encoding="utf-8")

    meta = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_name_or_path": model_name_or_path,
        "model_params_b_est": params_b,
        "seq_len": seq_len,
        "envelope": env,
        "selection": {"zero_stage": zero_stage, "offload_optimizer": offload_opt, "offload_param": offload_param},
        "output": str(out),
    }
    (run_dir / "ds_config.auto.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info(f"Wrote DeepSpeed config: {out} (stage={zero_stage}, offload_opt={offload_opt}, offload_param={offload_param})")
    return out


# ------------------------------------------------------------------------------
# lm-eval-harness integration + metrics JSON
# ------------------------------------------------------------------------------
def run_lm_eval(model_name_or_path: str, tasks_csv: str, batch_size: int, device: str, output_dir: Path,
                limit: Optional[int] = None, trust_remote_code: bool = False) -> Path:
    """
    Runs lm-eval-harness and writes a canonical metrics.json + run manifest.
    Prefers Python API if available; otherwise falls back to subprocess `lm_eval`.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    manifest_path = output_dir / "eval_manifest.json"

    tasks = [t.strip() for t in tasks_csv.split(",") if t.strip()]
    if not tasks:
        raise ValueError("No tasks provided. Example: --tasks mmlu,hellaswag")

    if not EXEC_POLICY.allow_lm_eval:
        raise RuntimeError("Execution policy denies lm-eval execution")

    if _HAS_LMEVAL:
        # Python API
        model = HFLM(
            pretrained=model_name_or_path,
            tokenizer=model_name_or_path,
            device=device,
            batch_size=batch_size,
            trust_remote_code=trust_remote_code,
        )
        res = lm_evaluator.simple_evaluate(
            model=model,
            tasks=tasks,
            batch_size=batch_size,
            limit=limit,
            log_samples=False,
        )
        # res includes "results" dict with metrics
        payload = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_name_or_path,
            "tasks": tasks,
            "batch_size": batch_size,
            "device": device,
            "limit": limit,
            "results": res.get("results", res),
        }
        metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        # CLI fallback (requires `lm_eval` entrypoint)
        cmd = [
            "lm_eval",
            "--model", "hf",
            "--model_args", f"pretrained={model_name_or_path},trust_remote_code={str(bool(trust_remote_code)).lower()}",
            "--tasks", ",".join(tasks),
            "--batch_size", str(batch_size),
            "--output_path", str(output_dir / "lm_eval_raw.json"),
        ]
        if limit is not None:
            cmd += ["--limit", str(limit)]
        proc = EXEC_POLICY.run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"lm_eval failed: {proc.stdout}\n{proc.stderr}")
        raw = json.loads((output_dir / "lm_eval_raw.json").read_text(encoding="utf-8"))
        payload = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_name_or_path,
            "tasks": tasks,
            "batch_size": batch_size,
            "device": device,
            "limit": limit,
            "results": raw.get("results", raw),
        }
        metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics_path": str(metrics_path),
        "exec_policy": {"mode": EXEC_POLICY.mode, "limits": EXEC_POLICY.limits.__dict__},
        "has_python_api": _HAS_LMEVAL,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Wrote lm-eval metrics: {metrics_path}")
    return metrics_path


# ------------------------------------------------------------------------------
# Architecture comparison chart generator (fed by metrics JSON)
# ------------------------------------------------------------------------------
def _load_metrics_file(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj


def compare_architecture(metrics_files: List[Path], output_dir: Path, label_from_parent_dir: bool = False) -> None:
    """
    Reads multiple metrics.json outputs and generates:
      - compare_summary.csv
      - compare_chart.png (bar chart per task metric)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    # gather task->metric->values
    by_task_metric: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(dict))

    def label_for(p: Path) -> str:
        if label_from_parent_dir:
            return p.parent.name
        return p.stem

    for mf in metrics_files:
        data = _load_metrics_file(mf)
        label = label_for(mf)
        results = data.get("results", {}) or {}
        # results is {task: {metric: value, ...}, ...}
        for task, m in results.items():
            if not isinstance(m, dict):
                continue
            for metric, val in m.items():
                if isinstance(val, (int, float)):
                    by_task_metric[task][metric][label] = float(val)

        # flatten into csv rows
        for task, m in results.items():
            if not isinstance(m, dict):
                continue
            flat = {"label": label, "task": task}
            for metric, val in m.items():
                if isinstance(val, (int, float)):
                    flat[metric] = float(val)
            rows.append(flat)

    df = pd.DataFrame(rows)
    csv_path = output_dir / "compare_summary.csv"
    df.to_csv(csv_path, index=False)

    # Chart: pick one "best" metric per task if possible
    # Prioritize: acc, acc_norm, mc2, exact_match, f1
    metric_priority = ["acc_norm", "acc", "mc2", "exact_match", "f1"]
    chart_rows = []
    for task, mm in by_task_metric.items():
        metric = None
        for mp in metric_priority:
            if mp in mm:
                metric = mp
                break
        if metric is None:
            # fallback first metric
            metric = sorted(mm.keys())[0] if mm else None
        if metric is None:
            continue
        for label, val in mm[metric].items():
            chart_rows.append({"task": task, "metric": metric, "label": label, "value": val})

    cdf = pd.DataFrame(chart_rows)
    if cdf.empty:
        logger.warning("No numeric metrics found to chart. CSV written only.")
        return

    # Produce per-task grouped bar chart
    # Keep top tasks by mean variance to show differences
    task_scores = []
    for task in cdf["task"].unique():
        vals = cdf[cdf["task"] == task]["value"].values
        if len(vals) >= 2:
            task_scores.append((task, float(np.std(vals))))
    task_scores.sort(key=lambda x: x[1], reverse=True)
    top_tasks = [t for t, _ in task_scores[:8]] if task_scores else list(cdf["task"].unique())[:8]
    cdf = cdf[cdf["task"].isin(top_tasks)]

    labels = sorted(cdf["label"].unique())
    tasks = list(dict.fromkeys(cdf["task"].tolist()))  # stable order
    width = 0.8 / max(1, len(labels))

    plt.figure(figsize=(12, 6))
    x = np.arange(len(tasks))
    for i, lab in enumerate(labels):
        vals = []
        for t in tasks:
            sel = cdf[(cdf["task"] == t) & (cdf["label"] == lab)]
            vals.append(float(sel["value"].iloc[0]) if len(sel) else float("nan"))
        plt.bar(x + i * width, vals, width=width, label=lab)
    plt.xticks(x + width * (len(labels) - 1) / 2, tasks, rotation=30, ha="right")
    plt.ylabel("score")
    plt.title("Architecture Comparison (lm-eval metrics)")
    plt.legend()
    plt.tight_layout()

    png_path = output_dir / "compare_chart.png"
    plt.savefig(png_path, dpi=200)
    plt.close()
    logger.info(f"Wrote comparison artifacts: {csv_path} and {png_path}")


# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="All-in-one verified post-training pipeline (v3).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_build = sub.add_parser("build", help="Build base dataset (SFT + preference) into run_dir.")
    ap_build.add_argument("--output_dir", type=str, required=True)
    ap_build.add_argument("--total_examples", type=int, default=250_000)
    ap_build.add_argument("--sft_ratio", type=float, default=DEFAULT_SFT_RATIO)
    ap_build.add_argument("--val_ratio", type=float, default=DEFAULT_VAL_RATIO)
    ap_build.add_argument("--seed", type=int, default=1337)

    ap_enrich = sub.add_parser("enrich", help="Run verifiers + reflexive improvement; writes enriched train+preference.")
    ap_enrich.add_argument("--run_dir", type=str, required=True)
    ap_enrich.add_argument("--runtime_model", type=str, required=True)
    ap_enrich.add_argument("--max_new_tokens", type=int, default=512)
    ap_enrich.add_argument("--num_candidates", type=int, default=3)
    ap_enrich.add_argument("--seed", type=int, default=1337)

    ap_enrich.add_argument("--domain1", type=str, default="domain_a")
    ap_enrich.add_argument("--domain2", type=str, default="domain_b")
    ap_enrich.add_argument("--domain1_keywords", type=str, default="finance,fx,bank,treasury,risk,portfolio,macroeconomics")
    ap_enrich.add_argument("--domain2_keywords", type=str, default="governance,law,policy,procurement,corruption,compliance")
    ap_enrich.add_argument("--domain1_corpora", type=str, default="", help="Comma-globs to local txt/jsonl for retrieval grounding.")
    ap_enrich.add_argument("--domain2_corpora", type=str, default="", help="Comma-globs to local txt/jsonl for retrieval grounding.")

    ap_sft = sub.add_parser("train_sft", help="Train SFT with TRL SFTTrainer.")
    ap_sft.add_argument("--run_dir", type=str, required=True)
    ap_sft.add_argument("--model_name_or_path", type=str, required=True)
    ap_sft.add_argument("--output_dir", type=str, required=True)
    ap_sft.add_argument("--max_seq_length", type=int, default=4096)
    ap_sft.add_argument("--packing", action="store_true")
    ap_sft.add_argument("--max_samples", type=int, default=None)

    ap_sft.add_argument("--learning_rate", type=float, default=2e-5)
    ap_sft.add_argument("--warmup_ratio", type=float, default=0.03)
    ap_sft.add_argument("--max_steps", type=int, default=20000)
    ap_sft.add_argument("--num_train_epochs", type=float, default=None)
    ap_sft.add_argument("--per_device_train_batch_size", type=int, default=1)
    ap_sft.add_argument("--gradient_accumulation_steps", type=int, default=16)
    ap_sft.add_argument("--weight_decay", type=float, default=0.0)
    ap_sft.add_argument("--lr_scheduler_type", type=str, default="cosine")
    ap_sft.add_argument("--max_grad_norm", type=float, default=1.0)
    ap_sft.add_argument("--logging_steps", type=int, default=20)
    ap_sft.add_argument("--save_steps", type=int, default=500)
    ap_sft.add_argument("--save_total_limit", type=int, default=3)
    ap_sft.add_argument("--seed", type=int, default=1337)
    ap_sft.add_argument("--bf16", action="store_true")
    ap_sft.add_argument("--fp16", action="store_true")
    ap_sft.add_argument("--gradient_checkpointing", action="store_true")
    ap_sft.add_argument("--trust_remote_code", action="store_true")

    ap_sft.add_argument("--lora_r", type=int, default=None)
    ap_sft.add_argument("--lora_alpha", type=int, default=64)
    ap_sft.add_argument("--lora_dropout", type=float, default=0.05)
    ap_sft.add_argument("--lora_target_modules", type=str, default="all")

    ap_dpo = sub.add_parser("train_dpo", help="Train preference alignment with TRL DPOTrainer or ORPOTrainer.")
    ap_dpo.add_argument("--run_dir", type=str, required=True)
    ap_dpo.add_argument("--model_name_or_path", type=str, required=True)
    ap_dpo.add_argument("--output_dir", type=str, required=True)
    ap_dpo.add_argument("--trainer", type=str, choices=["dpo", "orpo"], default="dpo")
    ap_dpo.add_argument("--beta", type=float, default=0.1)
    ap_dpo.add_argument("--max_prompt_length", type=int, default=1024)
    ap_dpo.add_argument("--max_length", type=int, default=4096)

    ap_dpo.add_argument("--learning_rate", type=float, default=2e-6)
    ap_dpo.add_argument("--warmup_ratio", type=float, default=0.03)
    ap_dpo.add_argument("--max_steps", type=int, default=8000)
    ap_dpo.add_argument("--num_train_epochs", type=float, default=None)
    ap_dpo.add_argument("--per_device_train_batch_size", type=int, default=1)
    ap_dpo.add_argument("--gradient_accumulation_steps", type=int, default=16)
    ap_dpo.add_argument("--weight_decay", type=float, default=0.0)
    ap_dpo.add_argument("--lr_scheduler_type", type=str, default="cosine")
    ap_dpo.add_argument("--max_grad_norm", type=float, default=1.0)
    ap_dpo.add_argument("--logging_steps", type=int, default=20)
    ap_dpo.add_argument("--save_steps", type=int, default=500)
    ap_dpo.add_argument("--save_total_limit", type=int, default=3)
    ap_dpo.add_argument("--seed", type=int, default=1337)
    ap_dpo.add_argument("--bf16", action="store_true")
    ap_dpo.add_argument("--fp16", action="store_true")
    ap_dpo.add_argument("--gradient_checkpointing", action="store_true")
    ap_dpo.add_argument("--trust_remote_code", action="store_true")

    ap_dpo.add_argument("--lora_r", type=int, default=None)
    ap_dpo.add_argument("--lora_alpha", type=int, default=64)
    ap_dpo.add_argument("--lora_dropout", type=float, default=0.05)
    ap_dpo.add_argument("--lora_target_modules", type=str, default="all")

    ap_snap = sub.add_parser("snapshot", help="Write compute envelope snapshot to run_dir.")
    ap_snap.add_argument("--run_dir", type=str, required=True)

    ap_ds = sub.add_parser("gen_deepspeed", help="Generate DeepSpeed config based on compute envelope.")
    ap_ds.add_argument("--run_dir", type=str, required=True)
    ap_ds.add_argument("--model_name_or_path", type=str, default="8b")
    ap_ds.add_argument("--per_device_train_batch_size", type=int, default=1)
    ap_ds.add_argument("--gradient_accumulation_steps", type=int, default=16)
    ap_ds.add_argument("--seq_len", type=int, default=4096)
    ap_ds.add_argument("--bf16", action="store_true")
    ap_ds.add_argument("--fp16", action="store_true")
    ap_ds.add_argument("--output_path", type=str, default=None)

    ap_eval = sub.add_parser("eval_lm", help="Run lm-eval-harness and write metrics JSON.")
    ap_eval.add_argument("--model_name_or_path", type=str, required=True)
    ap_eval.add_argument("--tasks", type=str, required=True, help="Comma-separated tasks, e.g. mmlu,hellaswag")
    ap_eval.add_argument("--batch_size", type=int, default=1)
    ap_eval.add_argument("--device", type=str, default="cuda:0" if torch.cuda.is_available() else "cpu")
    ap_eval.add_argument("--output_dir", type=str, required=True)
    ap_eval.add_argument("--limit", type=int, default=None)
    ap_eval.add_argument("--trust_remote_code", action="store_true")

    ap_cmp = sub.add_parser("compare_arch", help="Generate architecture comparison artifacts from metrics JSON files.")
    ap_cmp.add_argument("--metrics_glob", type=str, required=True)
    ap_cmp.add_argument("--output_dir", type=str, required=True)
    ap_cmp.add_argument("--label_from_parent_dir", action="store_true")

    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cmd = args.cmd

    if cmd == "build":
        out = Path(args.output_dir)
        build_dataset(out, args.total_examples, args.sft_ratio, args.val_ratio, args.seed)
        snap = compute_envelope_snapshot()
        (out / "compute_snapshot.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
        logger.info(f"Wrote compute_snapshot.json to {out}")
        return

    if cmd == "enrich":
        enrich_run_dir(
            run_dir=Path(args.run_dir),
            runtime_model_name=args.runtime_model,
            max_new_tokens=args.max_new_tokens,
            num_candidates=args.num_candidates,
            seed=args.seed,
            domain1=args.domain1,
            domain2=args.domain2,
            domain1_keywords=args.domain1_keywords,
            domain2_keywords=args.domain2_keywords,
            domain1_corpora=args.domain1_corpora,
            domain2_corpora=args.domain2_corpora,
        )
        return

    if cmd == "train_sft":
        train_sft(
            run_dir=Path(args.run_dir),
            model_name_or_path=args.model_name_or_path,
            output_dir=Path(args.output_dir),
            max_seq_length=args.max_seq_length,
            packing=bool(args.packing),
            max_samples=args.max_samples,
            learning_rate=args.learning_rate,
            warmup_ratio=args.warmup_ratio,
            max_steps=args.max_steps,
            num_train_epochs=args.num_train_epochs,
            per_device_train_batch_size=args.per_device_train_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            weight_decay=args.weight_decay,
            lr_scheduler_type=args.lr_scheduler_type,
            max_grad_norm=args.max_grad_norm,
            logging_steps=args.logging_steps,
            save_steps=args.save_steps,
            save_total_limit=args.save_total_limit,
            seed=args.seed,
            bf16=bool(args.bf16),
            fp16=bool(args.fp16),
            gradient_checkpointing=bool(args.gradient_checkpointing),
            trust_remote_code=bool(args.trust_remote_code),
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            lora_target_modules=args.lora_target_modules,
        )
        return

    if cmd == "train_dpo":
        train_dpo(
            run_dir=Path(args.run_dir),
            model_name_or_path=args.model_name_or_path,
            output_dir=Path(args.output_dir),
            trainer_kind=args.trainer,
            beta=args.beta,
            max_prompt_length=args.max_prompt_length,
            max_length=args.max_length,
            learning_rate=args.learning_rate,
            warmup_ratio=args.warmup_ratio,
            max_steps=args.max_steps,
            num_train_epochs=args.num_train_epochs,
            per_device_train_batch_size=args.per_device_train_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            weight_decay=args.weight_decay,
            lr_scheduler_type=args.lr_scheduler_type,
            max_grad_norm=args.max_grad_norm,
            logging_steps=args.logging_steps,
            save_steps=args.save_steps,
            save_total_limit=args.save_total_limit,
            seed=args.seed,
            bf16=bool(args.bf16),
            fp16=bool(args.fp16),
            gradient_checkpointing=bool(args.gradient_checkpointing),
            trust_remote_code=bool(args.trust_remote_code),
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            lora_target_modules=args.lora_target_modules,
        )
        return

    if cmd == "snapshot":
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        snap = compute_envelope_snapshot()
        (run_dir / "compute_snapshot.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
        logger.info(f"Wrote compute_snapshot.json to {run_dir}")
        return

    if cmd == "gen_deepspeed":
        out = Path(args.run_dir)
        output_path = Path(args.output_path) if args.output_path else None
        generate_deepspeed_config(
            run_dir=out,
            model_name_or_path=args.model_name_or_path,
            per_device_train_batch_size=args.per_device_train_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            bf16=bool(args.bf16),
            fp16=bool(args.fp16),
            seq_len=int(args.seq_len),
            output_path=output_path,
        )
        return

    if cmd == "eval_lm":
        run_lm_eval(
            model_name_or_path=args.model_name_or_path,
            tasks_csv=args.tasks,
            batch_size=int(args.batch_size),
            device=str(args.device),
            output_dir=Path(args.output_dir),
            limit=args.limit,
            trust_remote_code=bool(args.trust_remote_code),
        )
        return

    if cmd == "compare_arch":
        files = [Path(p) for p in glob.glob(args.metrics_glob)]
        if not files:
            raise FileNotFoundError(f"No metrics files matched: {args.metrics_glob}")
        compare_architecture(files, output_dir=Path(args.output_dir), label_from_parent_dir=bool(args.label_from_parent_dir))
        return


if __name__ == "__main__":
    main()
