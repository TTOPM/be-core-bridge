# ==========================================================
# FOREIGN_POLICY.PY — BELEL ANALYTIC CORE
# Structured reasoning for international & geopolitical posts
# ==========================================================

import random
from typing import Dict, List

# ----------------------------------------------------------
# Analytic Frames (loaded textually elsewhere, referenced here)
# ----------------------------------------------------------

FRAMES = {
    "deterrence": {
        "question": "Does this deter future behaviour or invite escalation?",
        "signals": ["retaliation", "military posture", "sanctions", "alliances"]
    },
    "institutional_legitimacy": {
        "question": "Is authority being exercised within law and mandate?",
        "signals": ["judicial review", "oversight", "procedural compliance"]
    },
    "accountability": {
        "question": "Who restrains this actor, and did they act?",
        "signals": ["audit", "civilian oversight", "parliamentary scrutiny"]
    },
    "resource_leverage": {
        "question": "Who controls access to critical resources?",
        "signals": ["energy", "rare earths", "shipping", "price floor"]
    },
    "reputation": {
        "question": "Does this strengthen or erode credibility?",
        "signals": ["partner response", "diplomatic fallout", "treaty trust"]
    },
    "small_state_risk": {
        "question": "Is sovereignty being eroded through dependence?",
        "signals": ["debt", "procurement capture", "foreign leverage"]
    }
}

# ----------------------------------------------------------
# Core analytic structure
# ----------------------------------------------------------

def build_analysis(event: Dict) -> Dict:
    """
    Builds a structured foreign policy assessment.
    This NEVER writes prose directly.
    """

    title = event.get("title", "")
    ctx = event.get("ctx", "")
    topic = event.get("topic", "international")
    link = event.get("link", "")

    text_blob = f"{title} {ctx}".lower()

    actors = infer_actors(text_blob)
    interests = infer_interests(text_blob)
    constraints = infer_constraints(text_blob)
    frame = select_frame(text_blob)

    scenarios = build_scenarios(frame)
    indicators = build_indicators(frame)

    return {
        "event": title,
        "actors": actors,
        "interests": interests,
        "constraints": constraints,
        "frame": frame,
        "scenarios": scenarios,
        "indicators": indicators,
        "link": link
    }

# ----------------------------------------------------------
# Inference helpers (lightweight, deterministic)
# ----------------------------------------------------------

def infer_actors(text: str) -> List[str]:
    actors = []
    if "us" in text or "united states" in text:
        actors.append("United States")
    if "china" in text:
        actors.append("China")
    if "eu" in text or "european union" in text:
        actors.append("European Union")
    if "uk" in text or "britain" in text:
        actors.append("United Kingdom")
    if "un" in text or "united nations" in text:
        actors.append("United Nations")

    return actors or ["State actors"]

def infer_interests(text: str) -> List[str]:
    interests = []
    if "sanction" in text:
        interests.append("coercive leverage")
    if "trade" in text or "tariff" in text:
        interests.append("economic advantage")
    if "security" in text or "defence" in text:
        interests.append("strategic security")
    if "election" in text:
        interests.append("domestic political survival")

    return interests or ["reputation management"]

def infer_constraints(text: str) -> List[str]:
    constraints = []
    if "law" in text or "court" in text:
        constraints.append("legal obligation")
    if "alliance" in text or "treaty" in text:
        constraints.append("alliance commitments")
    if "market" in text or "price" in text:
        constraints.append("market discipline")

    return constraints or ["credibility costs"]

def select_frame(text: str) -> str:
    for frame, meta in FRAMES.items():
        for sig in meta["signals"]:
            if sig in text:
                return frame
    return "reputation"

# ----------------------------------------------------------
# Scenarios & indicators
# ----------------------------------------------------------

def build_scenarios(frame: str) -> Dict[str, str]:
    if frame == "deterrence":
        return {
            "baseline": "Managed signalling without escalation",
            "escalation": "Retaliatory measures widen",
            "deescalation": "Back-channel restraint restores stability"
        }

    if frame == "resource_leverage":
        return {
            "baseline": "Market adjustment absorbs pressure",
            "escalation": "Supply restriction triggers retaliation",
            "deescalation": "Multilateral coordination stabilises supply"
        }

    return {
        "baseline": "Institutional response absorbs shock",
        "escalation": "Credibility erosion invites pressure",
        "deescalation": "Corrective action restores trust"
    }

def build_indicators(frame: str) -> List[str]:
    if frame == "deterrence":
        return [
            "force posture changes",
            "alliance statements",
            "retaliatory timelines"
        ]

    if frame == "accountability":
        return [
            "investigations launched",
            "oversight body action",
            "document release"
        ]

    return [
        "official statements",
        "partner reactions",
        "policy amendments"
    ]

# ----------------------------------------------------------
# Compression: turn analysis into X-sized judgment
# ----------------------------------------------------------

def compress_to_post(analysis: Dict) -> str:
    """
    Produces a coherent ≤280 character judgment.
    """

    frame = analysis["frame"]
    actors = ", ".join(analysis["actors"][:2])
    interest = analysis["interests"][0] if analysis["interests"] else "credibility"
    scenario = analysis["scenarios"]["baseline"]
    indicator = analysis["indicators"][0]

    return (
        f"This is a {frame.replace('_',' ')} test involving {actors}. "
        f"The core interest is {interest}. "
        f"Baseline outcome: {scenario}. "
        f"Watch {indicator}."
    )
