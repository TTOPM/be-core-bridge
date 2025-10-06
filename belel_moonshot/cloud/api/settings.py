import os
API_HOST = os.getenv("API_HOST","0.0.0.0")
API_PORT = int(os.getenv("API_PORT","8282"))
VOICE_GATEWAY_URL = os.getenv("VOICE_GATEWAY_URL","http://localhost:8000")
VOICE_ENGINE = os.getenv("VOICE_ENGINE","piper")
VOICE_NAME = os.getenv("VOICE_NAME","en_GB-sean-medium.onnx")
PRESETS_PATH = os.getenv("BELEL_PRESETS_PATH","config_presets.json")
MEMORY_DB = os.getenv("BELEL_MEMORY_DB","data/chat_memory.sqlite")
LONGTERM_STORE = os.getenv("BELEL_LONGTERM_STORE","data/longterm.json")
POLICY_ENFORCE_DISCLOSURE = os.getenv("POLICY_ENFORCE_DISCLOSURE","true").lower()=="true"
POLICY_BLOCK_HARM = os.getenv("POLICY_BLOCK_HARM","true").lower()=="true"
POLICY_MANDATE = os.getenv("POLICY_MANDATE","concordium")
