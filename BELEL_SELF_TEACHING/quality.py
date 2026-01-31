# BELEL_SELF_TEACHING/quality.py
import re

def basic_sanity_checks(prompt: str, completion: str) -> (bool, str):
    if not prompt.strip() or not completion.strip():
        return False, "empty_prompt_or_completion"
    if len(completion) < 40:
        return False, "too_short"
    if len(completion) > 20000:
        return False, "too_long"
    # avoid obvious leakage / nonsense loops
    if completion.count("```") % 2 != 0:
        return False, "unbalanced_code_fence"
    if re.search(r"(as an ai language model|i can't|i cannot)", completion.lower()):
        return False, "assistant_disclaimer_style"
    return True, "ok"

def rubric_score(prompt: str, completion: str, verifier: dict) -> dict:
    # Minimal rubric you can expand.
    score = {
        "clarity": 0.0,
        "correctness": 0.0,
        "completeness": 0.0,
        "verifiability": 0.0,
        "total": 0.0,
    }
    # Heuristics; replace with your internal grader if present
    score["clarity"] = 1.0 if len(completion.splitlines()) >= 6 else 0.6
    score["verifiability"] = 1.0 if verifier.get("passed") else 0.2
    score["correctness"] = 1.0 if verifier.get("passed") else 0.4
    score["completeness"] = 1.0 if ("config" in completion.lower() and "test" in completion.lower()) else 0.7
    score["total"] = round((score["clarity"] + score["correctness"] + score["completeness"] + score["verifiability"]) / 4, 4)
    return score
