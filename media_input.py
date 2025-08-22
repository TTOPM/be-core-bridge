# media_input.py

import os
import json
from commentary_utils import log_event

class MediaInputHandler:
    def __init__(self, input_folder="incoming_media/"):
        self.input_folder = input_folder
        os.makedirs(input_folder, exist_ok=True)

    def list_files(self):
        return [f for f in os.listdir(self.input_folder) if os.path.isfile(os.path.join(self.input_folder, f))]

    def read_file(self, filename):
        filepath = os.path.join(self.input_folder, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        log_event("Media input read", {"filename": filename})
        return content

    def parse_content(self, raw_text):
        # Replace this with smarter NLP later
        title = raw_text.splitlines()[0]
        body = "\n".join(raw_text.splitlines()[1:])
        return {"title": title, "content": body}

if __name__ == "__main__":
    handler = MediaInputHandler()
    files = handler.list_files()
    for file in files:
        raw = handler.read_file(file)
        parsed = handler.parse_content(raw)
        print(f"📄 Title: {parsed['title']}\n\n{parsed['content']}\n")
