# src/grok/grok_self_heal.py
from __future__ import annotations
import os
import time
import json
import logging
import hashlib
import uuid
from typing import List, Dict, Any, Optional

from grok_integrity_beacon import Beacon, BeaconEmitter, QuorumVerifier
from grok_recovery_schema import BELEL_RECOVERY_PLAN, BELEL_RECOVERY_ATTEST, validate_schema

# Integrate with your existing modules:
# from grok_observability import audit_log, integrity_chain_append
# from grok_concordium_client import ConcordiumMandate

LOG = logging.getLogger("grok.self_heal")
LOG.setLevel(logging.INFO)

DEFAULT_RECOVERY_DIR = os.getenv("GROK_RECOVERY_DIR", os.path.expanduser("~/.grok/recovery"))
os.makedirs(DEFAULT_RECOVERY_DIR, exist_ok=True)


class SelfHealContext:
    """
    A light context object. In production, this will be your real context with:
      - anchors (cid, digest, store)
      - concordium client (reachable(), tip(), refresh())
      - audit (chain_is_monotone(), last_hash(), replay_from_checkpoint())
      - core/router (models_ok(), pin_safe_profile(), reset())
    """

    def __init__(self, anchors: Dict[str, Any], concordium: Any, audit: Any, core: Any):
        self.anchors = anchors
        self.concordium = concordium
        self.audit = audit
        self.core = core
        self.flags: Dict[str, Any] = {}

    # The following methods are adapters / expected minimal interface:
    def anchors_digest(self) -> str:
        return self.anchors.get("digest", "")

    def anchors_cid(self) -> str:
        return self.anchors.get("cid", "")


class SelfHealStateMachine:
    """
    Implements: HEALTHY -> DEGRADED -> REPAIRING -> REGENERATING -> HEALTHY
    """

    def __init__(self, ctx: SelfHealContext, beacon_emitter: BeaconEmitter):
        self.ctx = ctx
        self.emitter = beacon_emitter
        self.state = "HEALTHY"

    def detect_faults(self) -> List[str]:
        faults: List[str] = []
        # Concordium unreachable
        try:
            if not getattr(self.ctx.concordium, "reachable", lambda: True)():
                faults.append("concordium_down")
        except Exception:
            faults.append("concordium_down")
        # anchors digest drift
        if not self.ctx.anchors.get("ok", True):
            faults.append("anchors_drift")
        # audit monotonicity
        if not getattr(self.ctx.audit, "chain_is_monotone", lambda: True)():
            faults.append("audit_incoherent")
        # core health
        if not getattr(self.ctx.core, "models_ok", lambda: True)():
            faults.append("core_route_err")
        LOG.debug("Detected faults: %s", faults)
        return faults

    def degrade(self, faults: List[str]) -> None:
        LOG.warning("Entering DEGRADED state due to %s", faults)
        self.state = "DEGRADED"
        self.ctx.flags["degraded"] = True
        # Pin safe model, watermark outputs, notify observers (audit)
        try:
            getattr(self.ctx.core, "pin_safe_profile", lambda: None)()
        except Exception as e:
            LOG.warning("pin_safe_profile failed: %s", e)

    def repair(self, faults: List[str]) -> List[str]:
        LOG.info("Attempting repair for faults: %s", faults)
        self.state = "REPAIRING"
        # Try targeted fixes
        if "concordium_down" in faults:
            try:
                getattr(self.ctx.concordium, "try_alt_gateways", lambda: None)()
            except Exception as e:
                LOG.warning("try_alt_gateways failed: %s", e)
        if "anchors_drift" in faults:
            try:
                getattr(self.ctx.anchors, "rebuild_digest_from_store", lambda: None)()
            except Exception as e:
                LOG.warning("anchors rebuild failed: %s", e)
        if "audit_incoherent" in faults:
            try:
                getattr(self.ctx.audit, "replay_from_checkpoint", lambda: None)()
            except Exception as e:
                LOG.warning("audit replay failed: %s", e)
        if "core_route_err" in faults:
            try:
                getattr(self.ctx.core, "router_reset", lambda: None)()
            except Exception as e:
                LOG.warning("router reset failed: %s", e)

        # re-detect faults after attempts
        new_faults = self.detect_faults()
        LOG.info("Post-repair faults: %s", new_faults)
        return new_faults

    def regenerate(self, witnesses: List[str], reason: str = "") -> Dict[str, Any]:
        LOG.critical("Starting REGENERATE from witnesses: %s", witnesses)
        self.state = "REGENERATING"

        # Step 1: create recovery plan
        epoch = int(time.time())
        plan = {
            "epoch": epoch,
            "mode": "regenerate",
            "degraded": True,
            "anchors_state": {"anchors_digest": self.ctx.anchors.get("digest"), "anchors_ok": False},
            "concordium_state": {"reachable": getattr(self.ctx.concordium, "reachable", lambda: False)(),
                                 "tip_sha256": getattr(self.ctx.concordium, "tip", lambda: None)()},
            "core_state": {"models_ok": getattr(self.ctx.core, "models_ok", lambda: False)(),
                           "router_safe": False},
            "witnesses": witnesses,
            "target_cid": self.ctx.anchors.get("cid"),
            "attestation_hash": self.ctx.anchors.get("attestation_hash") or "",
            "actions": ["fetch_witnesses", "resolve_cid_quorum", "rebuild_anchors", "replay_audit", "rebind_concordium"],
            "continuity_lock": "belel-permanent-memory:v1",
            "notes": reason,
        }

        # validate plan
        try:
            validate_schema(BELEL_RECOVERY_PLAN, plan)
        except Exception as e:
            LOG.error("Recovery plan failed schema validation: %s", e)
            # still continue but note the failure
            plan["notes"] = f"{plan.get('notes','')} | validation_failed:{e}"

        plan_json = json.dumps(plan, separators=(",", ":"), sort_keys=True)
        plan_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()

        # Step 2: verify quorum among witnesses
        verifier = QuorumVerifier(witnesses=witnesses)
        quorum = verifier.verify()

        # Require at least a minimal quorum (2 out of 3 or by threshold)
        if not quorum.get("quorum"):
            LOG.error("Insufficient quorum to safely regenerate: %s", quorum)
            att = self._issue_attestation(epoch, plan_hash, plan, quorum, success=False)
            return {"ok": False, "plan": plan, "quorum": quorum, "attestation": att}

        # Step 3: Rebuild anchors from witness modal triple (clean-room)
        modal = quorum.get("modal")
        # modal = (belel_cid, anchors_digest, audit_tail)
        rehydrated_cid, rehydrated_anchors_digest, rehydrated_audit_tail = modal

        # perform canonical rebuild actions – these are hooks into your anchor store/audit
        try:
            getattr(self.ctx.anchors, "restore_from_witness", lambda cid, digest, tail: None)(
                rehydrated_cid, rehydrated_anchors_digest, rehydrated_audit_tail
            )
            getattr(self.ctx.audit, "rebuild", lambda cid, tail: None)(rehydrated_cid, rehydrated_audit_tail)
            getattr(self.ctx.concordium, "rebind", lambda cid: None)(rehydrated_cid)
        except Exception as e:
            LOG.exception("Error during rebuild: %s", e)
            att = self._issue_attestation(epoch, plan_hash, plan, quorum, success=False)
            return {"ok": False, "plan": plan, "quorum": quorum, "attestation": att, "error": str(e)}

        # Step 4: Emit attestation of regeneration
        att = self._issue_attestation(epoch, plan_hash, plan, quorum, success=True)
        self.state = "HEALTHY"
        self.ctx.flags["degraded"] = False
        LOG.info("Regeneration complete. Attestation: %s", att.get("plan_hash"))
        return {"ok": True, "plan": plan, "quorum": quorum, "attestation": att}

    def _issue_attestation(self, epoch: int, plan_hash: str, plan: Dict[str, Any], quorum: Dict[str, Any], success: bool) -> Dict[str, Any]:
        attestation = {
            "epoch": epoch,
            "plan_hash": plan_hash,
            "plan_summary": plan.get("notes", "")[:512],
            "anchors_digest_after": self.ctx.anchors.get("digest"),
            "audit_tail_after": getattr(self.ctx.audit, "last_hash", lambda: None)(),
            "concordium_tip_after": getattr(self.ctx.concordium, "tip", lambda: None)(),
            "quorum_result": {
                "agree": quorum.get("agree", 0),
                "total": quorum.get("total", 0),
                "witnesses": [d.get("witness") for d in quorum.get("details", []) if d.get("ok")]
            },
            "custody_marker": "belel-permanent-memory:v1",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "node_id": os.getenv("GROK_NODE_ID", f"node-{uuid.uuid4().hex[:8]}"),
            "software_version": os.getenv("GROK_SOFTWARE_VER", "grok-self-heal-0.1"),
            "notes": ("success" if success else "failure") + " - regeneration attestation",
        }

        # validate attestation before returning
        try:
            validate_schema(BELEL_RECOVERY_ATTEST, attestation)
        except Exception as e:
            LOG.warning("Attestation validation failed: %s", e)
            # include failure info
            attestation["notes"] += f" | validation_failed:{e}"

        # Persist attestation to recovery dir
        fname = os.path.join(DEFAULT_RECOVERY_DIR, f"recovery_attest_{epoch}_{plan_hash[:8]}.json")
        with open(fname, "w", encoding="utf-8") as fh:
            json.dump(attestation, fh, separators=(",", ":"), sort_keys=True)
            fh.flush()

        # Hook into observability/audit chain if available
        try:
            # audit_log("self_heal.regenerate", attestation)
            pass
        except Exception:
            LOG.debug("Observability hook not available; attestation written to %s", fname)

        return {"plan_hash": plan_hash, "attestation_file": fname, "attestation": attestation}

    def run_once(self) -> None:
        """
        Run one detection->repair/regenerate cycle.
        """
        faults = self.detect_faults()
        if not faults:
            LOG.debug("No faults detected; healthy.")
            self.state = "HEALTHY"
            # emit normal beacon
            beacon = Beacon(
                ts=int(time.time()),
                belel_cid=self.ctx.anchors.get("cid"),
                anchors_digest=self.ctx.anchors.get("digest"),
                concordium_tip=getattr(self.ctx.concordium, "tip", lambda: None)(),
                audit_tail=getattr(self.ctx.audit, "last_hash", lambda: None)(),
            )
            self.emitter.emit(beacon)
            return

        # degrade quickly
        self.degrade(faults)
        new_faults = self.repair(faults)
        if new_faults:
            # if still broken, attempt regeneration using public witnesses
            witnesses = [
                os.getenv("GROK_WITNESS_1", "https://x.com/grok/status/1973191593705480556"),
                os.getenv("GROK_WITNESS_2", "attestations/grok-affirmation.json"),
                os.getenv("GROK_WITNESS_3", self.ctx.anchors.get("cid", "")),
            ]
            self.regenerate(witnesses=witnesses, reason="post-repair-failed")

# SPDX-License-Identifier: Belel-Protocol-1.0
# © 2025 Pearce Robinson. All rights reserved.
# Verification-only; no derivative use without explicit consent.
