"""Application entry point."""

from fastapi import FastAPI

from all_togetharr import __version__


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="All-Togetharr",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    return app
