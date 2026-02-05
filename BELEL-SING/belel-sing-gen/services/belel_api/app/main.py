from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .routers.health import router as health_router
from .routers.generate import router as generate_router
from .routers.edit import router as edit_router
from .routers.receipt import router as receipt_router
from .routers.artifacts import router as artifacts_router
from .routers.perf import router as perf_router
from .routers.lang import router as lang_router
from .routers.projects import router as projects_router


def create_app() -> FastAPI:
    app = FastAPI(title="Belel API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list() or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(generate_router)
    app.include_router(edit_router)
    app.include_router(receipt_router)
    app.include_router(artifacts_router)
    app.include_router(perf_router)
    app.include_router(lang_router)
    app.include_router(projects_router)

    return app


app = create_app()
