#!/usr/bin/env python3
import os
import json
import pathlib
import traceback
import yaml

from verifier.runners.verify_manifest import verify_manifest
from verifier.runners.verify_tweet_thread import verify_tweet_thread
from verifier.core.signer import sign_bundle
from verifier.core.canonical import canonical_json
from verifier.adapters.ipfs_client import pin_bytes_to_ipfs

CONFIG = pathlib.Path("config/targets.yaml")
OUTDIR = pathlib.Path("attestations")
OUTDIR.mkdir(exist_ok=True)

ENABLE_PIN = os.environ.get("ENABLE_IPFS_PIN", "0").strip().lower() in ("1", "true", "yes")


def _safe_subject(s: str) -> str:
    s = (s or "unknown_subject").strip()
    s = s.replace(":", "_").replace("/", "_")
    return s[:180]  # keep filenames sane


def _error_bundle(subject: str, kind: str, err: Exception) -> dict:
    return {
        "subject": subject,
        "ok": False,
        "kind": kind,
        "error": str(err),
        "trace": traceback.format_exc(limit=8),
    }


def write_bundle(subject: str, bundle: dict):
    """
    - signs bundle (if key exists; signer decides)
    - writes attestations/<subject>.json
    - optional IPFS pin (non-fatal)
    """
    subject = _safe_subject(subject)

    # Sign (signer decides what to do if key not present)
    try:
        bundle = sign_bundle(bundle)
    except Exception as e:
        # Never crash just because signing failed
        bundle = bundle or {}
        bundle["sign_error"] = str(e)

    path = OUTDIR / f"{subject}.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    # Optional IPFS pin (non-fatal)
    if ENABLE_PIN:
        try:
            data = canonical_json(bundle)
            ipfs_res = pin_bytes_to_ipfs(data)
            if isinstance(ipfs_res, dict) and ipfs_res.get("ok"):
                bundle["evidence_cid"] = ipfs_res.get("cid")
            else:
                bundle["ipfs_error"] = (ipfs_res or {}).get("error", "pin_failed")
        except Exception as e:
            bundle["ipfs_error"] = str(e)

        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "subject": subject,
        "integrity_hash": bundle.get("integrity_hash"),
        "file": str(path),
        "cid": bundle.get("evidence_cid"),
        "ok": bundle.get("ok", True) if isinstance(bundle, dict) else True,
    }


def _load_config() -> dict:
    if not CONFIG.exists():
        # Make it explicit and actionable
        raise FileNotFoundError(f"Missing config file: {CONFIG} (expected: config/targets.yaml)")

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    if not isinstance(cfg, dict):
        raise TypeError("config/targets.yaml must parse to a YAML mapping/object at top level.")
    return cfg


def _as_list(value) -> list:
    """Treat None/missing as empty list; error only on truly wrong types."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise TypeError(f"Expected a list (or null/omitted), got: {type(value).__name__}")


def main():
    cfg = _load_config()
    index = []

    # -------- GitHub manifests --------
    github_manifests = _as_list(cfg.get("github_manifests"))
    for i, item in enumerate(github_manifests):
        if not isinstance(item, dict):
            # Skip bad entries without killing the run
            b = _error_bundle(
                subject=f"github_manifest_{i}",
                kind="github_manifest",
                err=TypeError("github_manifests entries must be mapping objects"),
            )
            index.append(write_bundle(b["subject"], b))
            continue

        name = (item.get("name") or f"github_manifest_{i}").strip() or f"github_manifest_{i}"

        try:
            b = verify_manifest(
                name=name,
                file=item.get("file", "") or "",
                raw=item.get("raw", "") or "",
                html=item.get("html", "") or "",
                ipfs=item.get("ipfs", "") or "",
            )
        except Exception as e:
            b = _error_bundle(subject=name, kind="github_manifest", err=e)

        # Ensure a subject exists even if runner didn't provide it
        subj = b.get("subject") if isinstance(b, dict) else None
        subj = subj or f"manifest:{name}"
        index.append(write_bundle(subj, b))

    # -------- Tweet threads (optional) --------
    tweet_threads = _as_list(cfg.get("tweet_threads"))
    for i, item in enumerate(tweet_threads):
        if not isinstance(item, dict):
            b = _error_bundle(
                subject=f"tweet_thread_{i}",
                kind="tweet_thread",
                err=TypeError("tweet_threads entries must be mapping objects"),
            )
            index.append(write_bundle(b["subject"], b))
            continue

        name = (item.get("name") or f"tweet_thread_{i}").strip() or f"tweet_thread_{i}"
        status_url = (item.get("status_url") or "").strip()

        if not status_url:
            # Skip invalid entries but record it
            b = _error_bundle(
                subject=f"tweet:{name}",
                kind="tweet_thread",
                err=ValueError("tweet_threads entries require 'status_url'"),
            )
            index.append(write_bundle(b["subject"], b))
            continue

        try:
            b = verify_tweet_thread(name, status_url)
        except Exception as e:
            b = _error_bundle(subject=f"tweet:{name}", kind="tweet_thread", err=e)

        subj = b.get("subject") if isinstance(b, dict) else None
        subj = subj or f"tweet:{name}"
        index.append(write_bundle(subj, b))

    # -------- Write index --------
    (OUTDIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
