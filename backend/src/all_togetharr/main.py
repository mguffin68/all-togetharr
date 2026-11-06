"""Application entry point."""

from fastapi import FastAPI

from all_togetharr import __version__
from all_togetharr.platform.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="All-Togetharr",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    if settings is None:
        settings = Settings()

    app.state.settings = settings

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    return app
