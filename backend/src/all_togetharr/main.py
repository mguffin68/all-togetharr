"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from all_togetharr import __version__
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.migrations import run_migrations
from all_togetharr.platform.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(app.state.engine)
    yield
    engine = app.state.engine
    engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""
    if settings is None:
        settings = Settings()

    engine = create_db_engine(settings)
    session_factory = sessionmaker(bind=engine)

    app = FastAPI(
        title="All-Togetharr",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.get("/api/health")
    def health(request: Request):
        try:
            engine = request.app.state.engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok", "version": __version__}
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "version": __version__},
            )

    return app
