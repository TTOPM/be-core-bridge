# Simple CLI voice player that fetches and plays the WAV returned by the API.
# Requires: pip install requests simpleaudio

import requests, simpleaudio as sa, tempfile

def play(url: str):
    r = requests.get(url)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(r.content)
        path = f.name
    wave_obj = sa.WaveObject.from_wave_file(path)
    play_obj = wave_obj.play()
    play_obj.wait_done()
