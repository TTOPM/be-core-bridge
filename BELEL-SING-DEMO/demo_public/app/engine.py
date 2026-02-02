import httpx
from .config import settings
from .wav_utils import render_sine_melody_wav


class DemoEngineError(RuntimeError):
    pass


async def generate_demo_wav(lyrics: str, seconds: int) -> bytes:
    """
    Public demo generation:
    - seconds is forced to 3 or 5
    - lyrics is capped
    - if internal BELEL-SING is wired, call it privately
    - else synthesize a WAV
    """
    lyrics = (lyrics or "").strip()
    if len(lyrics) > settings.DEMO_MAX_LYRICS_CHARS:
        lyrics = lyrics[: settings.DEMO_MAX_LYRICS_CHARS]

    if seconds not in settings.DEMO_ALLOWED_SECONDS:
        seconds = settings.DEMO_DEFAULT_SECONDS

    # If internal service is configured, call it.
    if settings.BELEL_SING_INTERNAL_URL and settings.BELEL_SING_INTERNAL_TOKEN:
        url = settings.BELEL_SING_INTERNAL_URL.rstrip("/") + "/v1/sing/stream"
        headers = {
            "Authorization": f"Bearer {settings.BELEL_SING_INTERNAL_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "lyrics": lyrics,
            "seconds": seconds,
            "preset": "public_demo",
            # NOTE: keep this payload aligned with your internal handler shape.
            # If internal requires MIDI, you can store a fixed 5s demo MIDI server-side
            # and reference it by ID instead of accepting MIDI from the public.
        }

        timeout = httpx.Timeout(25.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code != 200:
                raise DemoEngineError(f"Internal engine error: HTTP {r.status_code}: {r.text[:200]}")
            # Expect WAV bytes from internal service
            return r.content

    # Fallback: always emit a real WAV so the public gets a sound artifact.
    return render_sine_melody_wav(
        seconds=seconds,
        watermark_gain=settings.DEMO_WATERMARK_GAIN,
    )
