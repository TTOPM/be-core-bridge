# BELEL_SELF_TEACHING/curriculum.py
LEVELS = [
    "1_Foundations",
    "2_Core_Methodologies",
    "3_Advanced_Self_Improvement",
    "4_Specialized_Domains",
    "5_Meta_Level_Evolution",
]

def assign_level(prompt: str, domain: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ["truth", "verify", "execution", "math", "unit test", "proof"]):
        return "1_Foundations"
    if any(k in p for k in ["pipeline", "dataset", "jsonl", "dpo", "sft", "etl", "dedup"]):
        return "2_Core_Methodologies"
    if any(k in p for k in ["active learning", "uncertainty", "self-play", "rlaif", "distill"]):
        return "3_Advanced_Self_Improvement"
    if domain and domain != "general":
        return "4_Specialized_Domains"
    return "5_Meta_Level_Evolution"
