#!/usr/bin/env python3

import hashlib
import os

WATERMARK = """
<!--
🛡️ Belel Authorship Lock
Hash: {hash}
Author: Pearce Robinson
Protocol: https://github.com/TTOPM/be-core-bridge
License: Belel Shield License v1.1
-->
"""

TARGET_EXTENSIONS = [".md", ".json", ".yml", ".txt"]

def generate_hash(filepath):
    with open(filepath, "rb") as f:
        file_data = f.read()
    return hashlib.sha256(file_data).hexdigest()

def append_watermark(filepath):
    if filepath.endswith(".md"):
        mode = "a"
    else:
        mode = "a"

    hash_val = generate_hash(filepath)
    with open(filepath, mode, encoding="utf-8") as f:
        f.write(WATERMARK.format(hash=hash_val))
    print(f"[🔐] Watermarked: {filepath}")

def main():
    for root, dirs, files in os.walk("."):
        for file in files:
            if any(file.endswith(ext) for ext in TARGET_EXTENSIONS):
                filepath = os.path.join(root, file)
                append_watermark(filepath)

if __name__ == "__main__":
    main()
