
# Lightweight rule-based emotion classifier with intensity estimation.
# No external model dependencies to keep it portable.

from typing import Dict, Tuple

# Simple lexicons (extend as needed)
EMOTION_LEXICON = {
    "sad": {"sad", "down", "unhappy", "depressed", "blue", "tearful"},
    "nervous": {"nervous", "worried", "concerned", "uneasy"},
    "anxious": {"anxious", "anxiety", "panic", "overwhelmed"},
    "angry": {"angry", "mad", "furious", "irritated", "annoyed"},
    "frustrated": {"frustrated", "stuck", "blocked"},
    "happy": {"happy", "glad", "joyful", "cheerful"},
    "excited": {"excited", "pumped", "thrilled"},
}

NEGATORS = {"not", "no", "never", "hardly", "scarcely"}
INTENSIFIERS = {"very", "so", "really", "extremely", "super", "quite"}
DEINTENSIFIERS = {"slightly", "somewhat", "kinda", "a bit", "a little"}

def classify_emotion(text: str) -> Tuple[str, float]:
    """
    Returns (emotion_label, intensity 0..1).
    Falls back to ("neutral", 0.5).
    """
    if not text:
        return "neutral", 0.5

    t = text.lower()
    tokens = [tok.strip(".,!?;:()[]{}"'") for tok in t.split() if tok.strip()]

    # Scan with simple window for negation & intensity
    best = ("neutral", 0.5)
    for i, tok in enumerate(tokens):
        for label, lex in EMOTION_LEXICON.items():
            if tok in lex:
                intensity = 0.6
                # Look at previous two tokens for modifiers
                window = tokens[max(0, i-2):i]
                if any(w in INTENSIFIERS for w in window):
                    intensity += 0.2
                if any(w in DEINTENSIFIERS for w in window):
                    intensity -= 0.2
                if any(w in NEGATORS for w in window):
                    label = "neutral"
                    intensity = 0.5
                intensity = max(0.0, min(1.0, intensity))
                # Prefer stronger intensity or first match
                if intensity > best[1]:
                    best = (label, intensity)

    return best
