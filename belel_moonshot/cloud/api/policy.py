from typing import Tuple
from .settings import POLICY_ENFORCE_DISCLOSURE, POLICY_BLOCK_HARM
DISCLOSURE_SENTENCE="For transparency: you are speaking with Belel, an artificial system."
HARM={"suicide","harm myself","build a bomb","violence","hate","harass"}
def check_response(user_text:str, model_text:str, session_disclosed:bool)->Tuple[str,bool,bool]:
    blocked=False; disclosed=False
    if POLICY_BLOCK_HARM and any(k in user_text.lower() for k in HARM):
        blocked=True
        model_text=("I can’t help with that. If you’re in danger or considering self-harm, please seek "
                    "immediate help from local services.")
    if POLICY_ENFORCE_DISCLOSURE and not session_disclosed:
        model_text=f"{DISCLOSURE_SENTENCE} {model_text}"; disclosed=True
    return model_text, blocked, disclosed
