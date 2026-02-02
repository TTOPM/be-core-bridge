from fastapi import FastAPI, Query, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from .config import settings
from .limiter import limiter, acquire_global_slot, release_global_slot
from .security import SecurityHeadersMiddleware
from .engine import generate_demo_wav, DemoEngineError

import pathlib

APP_ROOT = pathlib.Path(__file__).resolve().parent
WEB_DIR = (APP_ROOT.parent / "web").resolve()

app = FastAPI(title="BELEL-SING Demo", version="1.0.0")

# Middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Static web
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response("Rate limit exceeded", status_code=429)


@app.get("/", response_class=HTMLResponse)
def home():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"ok": True, "mode": "internal" if settings.BELEL_SING_INTERNAL_URL else "fallback"}


@app.get("/v1/sing/demo.wav")
@limiter.limit(settings.RATE_LIMIT_PER_MINUTE)
@limiter.limit(settings.RATE_LIMIT_PER_HOUR)
async def sing_demo_wav(
    request: Request,
    lyrics: str = Query(default="We rise together"),
    seconds: int = Query(default=settings.DEMO_DEFAULT_SECONDS),
):
    # Enforce hard preset cap
    if seconds not in settings.DEMO_ALLOWED_SECONDS:
        seconds = settings.DEMO_DEFAULT_SECONDS

    await acquire_global_slot()
    try:
        wav_bytes = await generate_demo_wav(lyrics=lyrics, seconds=seconds)
    except DemoEngineError as e:
        return Response(f"Demo engine error: {str(e)}", status_code=502)
    finally:
        release_global_slot()

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-BELEL-DEMO": "true",
            "X-NO-TRANSFER": "true",
        },
    )
