"""Belel self-hosted full-duplex PROTOCOL TRANSLATOR (opt-in only).

Translates Belel's JSON PCM16 frames to Kyutai Moshi-family binary WebSocket
messages (Opus audio 0x01; output text 0x02; 0x00 handshake). PersonaPlex uses
a related stack; validate its installed server version before selecting it.

This file does not install Moshi / PersonaPlex or download weights. Launch the
model server separately following the official model instructions. It requires
a trained, running model upstream; without one it returns a health/error event.

Security: loopback only, strict Origin allowlist and optional ephemeral session token.
No microphone capture, disk recordings, assistant commands, or playback.

Example:
  export BELEL_DUPLEX_UPSTREAM=ws://127.0.0.1:8998/api/chat
  export BELEL_DUPLEX_ALLOWED_ORIGIN=http://localhost:8080
  export BELEL_DUPLEX_TOKEN='a-long-random-token'
  python duplex_proxy.py
"""
from __future__ import annotations
import asyncio
import base64
import json
import os
from urllib.parse import urlparse
import opuslib
from websockets.legacy.server import serve
from websockets.legacy.client import connect

PORT = int(os.environ.get('BELEL_DUPLEX_PORT', '8792'))
UPSTREAM = os.environ.get('BELEL_DUPLEX_UPSTREAM', '').strip()
ALLOWED_ORIGIN = os.environ.get('BELEL_DUPLEX_ALLOWED_ORIGIN', 'http://localhost:8080')
SESSION_TOKEN = os.environ.get('BELEL_DUPLEX_TOKEN', '').strip()
if UPSTREAM:
    u = urlparse(UPSTREAM)
    if u.scheme not in ('ws', 'wss'):
        raise SystemExit('BELEL_DUPLEX_UPSTREAM must be ws/wss')
    if u.scheme == 'ws' and u.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise SystemExit('Unencrypted model links are permitted only to loopback')


def encode_pcm_to_moshi(pcm: bytes, enc: opuslib.Encoder) -> list[bytes]:
    if len(pcm) % 2 or len(pcm) > 48000: raise ValueError('Invalid PCM frame')
    # Opus supports 20ms, 24kHz mono = 480 samples = 960 bytes.
    chunks=[]
    for n in range(0,len(pcm)//960*960,960):
        packet = enc.encode(pcm[n:n+960],480)
        chunks.append(bytes([1])+packet)
    return chunks


def decode_moshi_packet(message: bytes, dec: opuslib.Decoder) -> dict | None:
    if not message: return None
    if message[0] == 0: return {'type':'health', 'detail':'upstream_handshake'}
    if message[0] == 2:
        return {'type':'transcript.delta', 'text':message[1:].decode('utf-8','replace')[:2000]}
    if message[0] == 1:
        pcm = dec.decode(message[1:], 5760)
        if not pcm: return None
        return {'type':'audio.delta','sample_rate':24000,'pcm16le_b64':base64.b64encode(pcm).decode('ascii')}
    return None


async def handle(client, _path):
    # This is intentionally not a public web endpoint: only trusted local clients.
    if client.request_headers.get('Origin') != ALLOWED_ORIGIN:
        await client.close(code=1008, reason='origin_denied'); return
    if not UPSTREAM:
        await client.send(json.dumps({'type':'error','detail':'self_hosted_model_not_configured'}))
        await client.close(); return
    try:
        raw_hello = await asyncio.wait_for(client.recv(),timeout=5)
        hello = json.loads(raw_hello) if isinstance(raw_hello,str) else {}
        if hello.get('type') != 'hello' or hello.get('schema') != 'belel.duplex.v1' or (SESSION_TOKEN and hello.get('token') != SESSION_TOKEN):
            await client.close(code=1008,reason='unauthorized'); return
        enc = opuslib.Encoder(24000,1,opuslib.APPLICATION_VOIP)
        dec = opuslib.Decoder(24000,1)
        async with connect(UPSTREAM, max_size=2**22, open_timeout=10) as model:
            await client.send(json.dumps({'type':'health','detail':'duplex_model_connected'}))
            async def receive_model():
                async for msg in model:
                    if not isinstance(msg, bytes): continue
                    event=decode_moshi_packet(msg,dec)
                    if event: await client.send(json.dumps(event))
            async def receive_client():
                async for msg in client:
                    if not isinstance(msg,str) or len(msg)>180000: continue
                    try: data=json.loads(msg)
                    except json.JSONDecodeError: continue
                    if data.get('type')=='close': break
                    if data.get('type') != 'audio.frame' or data.get('sample_rate') != 24000: continue
                    try: pcm=base64.b64decode(data['pcm16le_b64'],validate=True)
                    except (ValueError,KeyError): continue
                    for packet in encode_pcm_to_moshi(pcm,enc): await model.send(packet)
            a=asyncio.create_task(receive_model()); b=asyncio.create_task(receive_client());
            done,pending=await asyncio.wait([a,b],return_when=asyncio.FIRST_COMPLETED)
            for task in pending: task.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
            for task in done:
                exc=task.exception()
                if exc: raise exc
    except Exception as exc:
        try: await client.send(json.dumps({'type':'error','detail':'model_session_failed'}))
        except Exception: pass
        print(f'Belel duplex session failed ({type(exc).__name__}); no audio logged')
    finally:
        await client.close()


async def main():
    print(f'Belel local duplex translator on ws://127.0.0.1:{PORT}; upstream={bool(UPSTREAM)}')
    async with serve(handle,'127.0.0.1',PORT,max_size=180000,ping_interval=15):
        await asyncio.Future()

if __name__=='__main__':
    asyncio.run(main())
