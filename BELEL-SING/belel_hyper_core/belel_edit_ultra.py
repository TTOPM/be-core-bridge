# BELEL-SING/belel-sing-gen/belel_edit_ultra.py
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

import torch

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest
from belel_hyper_core.belel_editing import BelelEditSpec, repaint_latent, seconds_to_latent_range


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main():
    ap = argparse.ArgumentParser()

    # base generation
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=None)

    # checkpoints
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)

    # output
    ap.add_argument("--out_dir", default="outputs/belel_ultra")
    ap.add_argument("--name", default=None)

    # multi-language plumbing
    ap.add_argument("--lang", default="auto", help="Language tag, e.g. en, es, fr, hi, ar, zh, auto")

    # editing controls
    ap.add_argument("--mode", default="retake", choices=["repaint", "retake", "lyric_edit", "extend"])
    ap.add_argument("--edit_start", type=float, default=10.0, help="start seconds (for repaint/retake/lyric_edit)")
    ap.add_argument("--edit_end", type=float, default=20.0, help="end seconds (for repaint/retake/lyric_edit)")
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--feather", type=int, default=12)

    # lyric edit payload
    ap.add_argument("--new_lyrics", default=None, help="Only used for --mode lyric_edit")

    # extend payload
    ap.add_argument("--extend_by", type=int, default=30, help="seconds to extend by (v1 regen full with longer duration)")

    # runtime
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")

    args = ap.parse_args()

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=int(args.steps),
        guidance=float(args.guidance),
        seed=args.seed,
        out_dir=args.out_dir,
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
        # 2-step stability defaults already in engine config; keep them there
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    # --- Mode: EXTEND (v1)
    # v1 is intentionally honest: you regenerate with longer duration (no stitching yet).
    # You will still have exact provenance + scoring.
    if args.mode == "extend":
        req = BelelHyperRequest(
            prompt=args.prompt,
            lyrics=args.lyrics,
            duration_sec=int(args.duration) + int(args.extend_by),
            filename=args.name,
            steps=int(args.steps),
            guidance=float(args.guidance),
            extra={"edit_suite": True, "mode": "extend_v1", "lang": args.lang, "utc": _utc()},
        )
        out = engine.run(req)
        print("wav:", out["wav_path"])
        print("mel:", out["mel_path"])
        print("wav_sidecar:", out["wav_sidecar"])
        return

    # --- For repaint/retake/lyric_edit we do a two-pass:
    # 1) generate base latent x + base mel (but we need latent x to repaint; so we call internal latent path)
    # To avoid changing your engine public API too much, we reproduce the engine latent steps here using its modules.

    # Build conditioning (language tag is enforced by prefixing prompt; BELEL-owned and deterministic)
    # You can later move this into BelelConditioner itself.
    prompt_tagged = f"[BELEL_LANG={args.lang}] {args.prompt}".strip()

    req_base = BelelHyperRequest(
        prompt=prompt_tagged,
        lyrics=args.lyrics,
        duration_sec=int(args.duration),
        filename=args.name,
        steps=int(args.steps),
        guidance=float(args.guidance),
        extra={"edit_suite": True, "mode": "base_for_edit", "lang": args.lang, "utc": _utc()},
    )

    # --- replicate engine.generate_mel but keep latent x0 result path available
    steps = int(req_base.steps or cfg.steps)
    guidance = float(req_base.guidance or cfg.guidance)

    device = torch.device(cfg.device)
    dt = torch.float16 if str(cfg.dtype).lower() == "float16" else (torch.bfloat16 if str(cfg.dtype).lower() == "bfloat16" else torch.float32)

    cond = engine.cond(req_base.prompt, req_base.lyrics, device=str(cfg.device))

    frames = max(64, int((cfg.sample_rate * int(req_base.duration_sec)) / cfg.hop_length))
    latent_T = max(64, frames // 4)
    x_init = torch.randn(1, int(cfg.latent_ch), int(latent_T), device=device, dtype=dt)

    # Solve base
    preset = engine.preset2 if steps == 2 else None
    x_base = engine.solver.generate(
        x_init,
        cond,
        steps=steps,
        guidance=guidance,
        preset=preset,
        clamp_pred=float(cfg.clamp_pred),
        cfg_rescale=float(cfg.cfg_rescale) if steps == 2 else 0.0,
    )

    # Edit region mapping in latent time
    i0, i1 = seconds_to_latent_range(
        start_sec=float(args.edit_start),
        end_sec=float(args.edit_end),
        duration_sec=float(req_base.duration_sec),
        latent_T=int(latent_T),
    )

    # Mode behavior
    if args.mode == "lyric_edit":
        if not args.new_lyrics:
            raise SystemExit("--new_lyrics is required for --mode lyric_edit")
        cond_new = engine.cond(req_base.prompt, str(args.new_lyrics), device=str(cfg.device))
        cond_use = cond_new
        mode_tag = "lyric_edit"
    elif args.mode == "repaint":
        cond_use = cond
        mode_tag = "repaint"
    else:  # retake
        cond_use = cond
        mode_tag = "retake"

    edit = BelelEditSpec(
        start_t=int(i0),
        end_t=int(i1),
        strength=float(args.strength if args.mode != "retake" else 1.0),
        feather=int(args.feather),
    )

    def solver_fn(x, cond, **kw):
        return engine.solver.generate(x, cond, **kw)

    x_edited, edit_meta = repaint_latent(
        solver_fn,
        x_init=x_base,
        cond=cond_use,
        steps=steps,
        guidance=guidance,
        clamp_pred=float(cfg.clamp_pred),
        cfg_rescale=float(cfg.cfg_rescale) if steps == 2 else 0.0,
        edit=edit,
        preset=preset,
        seed=args.seed,
    )

    mel = engine.codec.decode(x_edited.float())
    mel = engine.__class__.generate_mel.__globals__["belel_minmax_to_range"](mel, -4.0, 4.0)  # uses engine’s function without importing internals

    wav = engine.mel_to_waveform(mel)

    # Write outputs through engine persistence to keep provenance identical
    base_name = args.name or f"belel_edit_{mode_tag}_{int(time.time())}.wav"
    if not base_name.lower().endswith(".wav"):
        base_name += ".wav"

    wav_path = engine.save_wav(wav, base_name)

    meta: Dict[str, Any] = {
        "utc": _utc(),
        "preset": str(cfg.preset),
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": None if cfg.seed is None else int(cfg.seed),
        "dtype": str(cfg.dtype),
        "codec_ckpt": str(cfg.codec_ckpt or ""),
        "denoiser_ckpt": str(cfg.denoiser_ckpt or ""),
        "edit_suite": True,
        "edit_mode": mode_tag,
        "lang": str(args.lang),
        **edit_meta,
    }
    if args.mode == "lyric_edit":
        meta["lyrics_old_hash"] = str(hash(req_base.lyrics))
        meta["lyrics_new_hash"] = str(hash(args.new_lyrics))

    mel_path = engine.save_mel_sidecar_pt(
        mel,
        base_name,
        prompt=req_base.prompt,
        lyrics=(args.new_lyrics if args.mode == "lyric_edit" else req_base.lyrics),
        meta=meta,
    )
    wav_sidecar = engine.save_wav_sidecar_json(
        wav_path,
        prompt=req_base.prompt,
        lyrics=(args.new_lyrics if args.mode == "lyric_edit" else req_base.lyrics),
        meta=meta,
    )

    print("wav:", wav_path)
    print("mel:", mel_path)
    print("wav_sidecar:", wav_sidecar)


if __name__ == "__main__":
    main()
