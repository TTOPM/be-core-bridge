# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_presets.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class BelelInferenceDefaults:
    # Core
    steps: int = 2
    guidance: float = 6.0

    # 2-step time knots (locked)
    # These are "noise scale" style knots for the simple x = x0 + t * noise training used in your distillers.
    # If you later switch to a sigma/scheduler formalism, you’ll map these accordingly.
    t0: float = 1.0
    t1: float = 0.25

    # Stability
    clamp_pred: float = 10.0              # clamps model prediction magnitude
    dynamic_cap: bool = True              # cap guidance effect dynamically
    cap_k: float = 3.0                    # tighter => safer; looser => punchier

    # Optional CFG-like rescale behaviour (helps prevent over-saturation when guidance is high)
    cfg_rescale: float = 0.7              # 0 disables; 0.5–0.8 recommended

    # Performance/precision
    dtype: str = "float16"                # float16 is fastest; bfloat16 if your GPU supports it well
    tf32: bool = True                     # safe speedup on Ampere+
    compile: bool = True                  # torch.compile when available

    # Output/provenance
    write_sidecars: bool = True
    auto_score: bool = False
    auto_log: bool = False
    min_score: float = 7.5

    @staticmethod
    def ultra2() -> "BelelInferenceDefaults":
        """
        Final locked 2-step defaults (stable + aggressive).
        """
        return BelelInferenceDefaults(
            steps=2,
            guidance=6.0,
            t0=1.0,
            t1=0.25,
            clamp_pred=10.0,
            dynamic_cap=True,
            cap_k=3.0,
            cfg_rescale=0.7,
            dtype="float16",
            tf32=True,
            compile=True,
            write_sidecars=True,
            auto_score=False,
            auto_log=False,
            min_score=7.5,
        )

    def as_meta(self) -> Dict[str, Any]:
        return {
            "preset": "ultra2",
            "steps": int(self.steps),
            "guidance": float(self.guidance),
            "t_knots": [float(self.t0), float(self.t1)],
            "clamp_pred": float(self.clamp_pred),
            "dynamic_cap": bool(self.dynamic_cap),
            "cap_k": float(self.cap_k),
            "cfg_rescale": float(self.cfg_rescale),
            "dtype": str(self.dtype),
            "tf32": bool(self.tf32),
            "compile": bool(self.compile),
        }
