from typing import List, Tuple
from .emotions import classify
def generate_reply(history:List[Tuple[str,str,str]], user_text:str, persona:str, emotion_hint:str=None)->str:
    label,_=classify(user_text)
    mood=emotion_hint or label
    style={"sad":"gentle","nervous":"calm","anxious":"soothing","angry":"steady",
           "frustrated":"reassuring","happy":"warm","excited":"enthusiastic","neutral":"clear"}.get(mood,"clear")
    return f"I’m here with you, in a {style} way. You said: “{user_text}”. Let’s move forward together. (persona={persona})"
