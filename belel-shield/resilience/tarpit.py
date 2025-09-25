#!/usr/bin/env python3
"""
Belel Tarpit
Creates a simple tarpit server that accepts connections but never responds.
This ties up hostile bots without sending traffic back.
"""

import socket

HOST = "0.0.0.0"
PORT = 8080

def run_tarpit():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"🪤 Belel Tarpit listening on {HOST}:{PORT} ...")
        while True:
            conn, addr = s.accept()
            print(f"[+] Tarpitted connection from {addr}")
            # Do nothing — connection stays open forever

if __name__ == "__main__":
    run_tarpit()
