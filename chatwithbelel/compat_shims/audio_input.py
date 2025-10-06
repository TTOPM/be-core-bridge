import sys, asyncio, websockets, sounddevice as sd, soundfile as sf, queue, numpy as np, os

# Simple CLI recorder that streams raw chunks to Belel STT WS for testing.
# Requires: pip install sounddevice soundfile websockets numpy

RATE = 16000
CHUNK_MS = 250

async def stream_ws(uri):
    q = queue.Queue()
    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=RATE, blocksize=int(RATE*CHUNK_MS/1000),
                           dtype='int16', channels=1, callback=callback):
        async with websockets.connect(uri) as ws:
            print("Connected to", uri)
            try:
                while True:
                    data = q.get()
                    await ws.send(data)
                    msg = await ws.recv()
                    print("WS:", msg)
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    host = os.getenv("VOICE_GATEWAY_URL", "http://localhost:8000").replace("http://","").replace("https://","")
    uri = f"ws://{host}/v1/asr/stream"
    asyncio.run(stream_ws(uri))
