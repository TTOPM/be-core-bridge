import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import settings


limiter = Limiter(key_func=get_remote_address)

# Process-level concurrency gate (simple, effective)
_global_sem = asyncio.Semaphore(settings.GLOBAL_CONCURRENCY)


async def acquire_global_slot():
    await _global_sem.acquire()


def release_global_slot():
    try:
        _global_sem.release()
    except ValueError:
        pass
