# Bridge responder that you can swap with your proprietary Belel LLM.
# The function signature mirrors your legacy code so existing imports won't break.

from typing import List, Tuple
from backend.main import generate_reply as _gen
from backend import memory

def get_belel_reply(history: List[Tuple[str, str, str]], user_text: str, emotion_label: str) -> str:
    # history shape: [(role, content, ts), ...]
    return _gen(history, user_text, emotion_label)
