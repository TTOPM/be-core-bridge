
# observability.py — request/response timing middleware
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        resp = await call_next(request)
        dur = (time.perf_counter()-start)*1000.0
        resp.headers["X-Server-Timing-ms"] = f"{dur:.1f}"
        return resp

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
registry = CollectorRegistry()
REQS = Counter("belel_requests_total","Total requests",registry=registry)
LAT = Histogram("belel_request_duration_ms","Request latency (ms)",registry=registry)
metrics_router = APIRouter()
@metrics_router.get("/metrics")
def metrics():
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
