"""Belel sovereign on-device/local-network wake inference.

Requires a LICENSED separately trained 'Hey Belel' .onnx/.tflite model.
Binds ONLY to loopback; never writes received audio or transcripts to disk.
Run: BELEL_WAKE_MODEL=/absolute/path/to/hey_belel.onnx python wake_server.py
"""
from __future__ import annotations
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
import numpy as np

MODEL_PATH = os.environ.get('BELEL_WAKE_MODEL', '').strip()
PORT = int(os.environ.get('BELEL_WAKE_PORT', '8791'))
if not MODEL_PATH or not Path(MODEL_PATH).is_file():
    raise SystemExit('BELEL_WAKE_MODEL must point to a separately licensed, trained model file')

from openwakeword.model import Model  # installed only in optional runtime
model = Model(wakeword_models=[MODEL_PATH])
lock = Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log request contents or user IP beyond the loopback binding.
        return

    def respond(self, code: int, payload: dict):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        # Local app/browser may require CORS; only explicitly configured origin is allowed.
        origin = self.headers.get('Origin')
        allowed = os.environ.get('BELEL_WAKE_ALLOWED_ORIGIN', 'http://localhost:8080')
        if origin == allowed:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self.headers.get('Origin')
        allowed = os.environ.get('BELEL_WAKE_ALLOWED_ORIGIN', 'http://localhost:8080')
        if origin != allowed:
            self.respond(403, {'error':'origin_denied'})
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self.respond(200, {'engine':'openwakeword','model':'owner-supplied','ready':True,'recordings_saved':False})
        else: self.respond(404, {'error':'not_found'})

    def do_POST(self):
        if self.path != '/v1/wake': return self.respond(404, {'error':'not_found'})
        origin = self.headers.get('Origin')
        allowed = os.environ.get('BELEL_WAKE_ALLOWED_ORIGIN', 'http://localhost:8080')
        if origin and origin != allowed: return self.respond(403, {'error':'origin_denied'})
        try:
            n = int(self.headers.get('Content-Length','0'))
            if n <= 0 or n > 120000: return self.respond(413, {'error':'oversize'})
            req = json.loads(self.rfile.read(n))
            if req.get('sample_rate') != 16000: return self.respond(400, {'error':'sample_rate_must_be_16000'})
            audio = base64.b64decode(req['pcm16le_b64'], validate=True)
            if len(audio) < 256 or len(audio) > 64000 or len(audio)%2: return self.respond(400, {'error':'bad_pcm_frame'})
            samples = np.frombuffer(audio, dtype='<i2')
            max_score = 0.0
            with lock:
                # openWakeWord accepts 16kHz signed PCM samples; 80ms (1280 samples) is its standard step.
                for offset in range(0, len(samples), 1280):
                    frame = samples[offset:offset+1280]
                    if len(frame) < 1280: break
                    pred = model.predict(frame)
                    if pred: max_score = max(max_score, *(float(v) for v in pred.values()))
            return self.respond(200, {'confidence':max(0.0,min(1.0,max_score))})
        except Exception:
            return self.respond(400, {'error':'invalid_request'})

if __name__ == '__main__':
    print(f'Belel acoustic wake service listening on 127.0.0.1:{PORT}; no capture or storage')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
