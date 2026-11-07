"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from all_togetharr import __version__
from all_togetharr.platform.auth.routes import router as auth_router
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.jobs.runner import JobRunner
from all_togetharr.platform.logging import RequestLoggingMiddleware, configure_logging
from all_togetharr.platform.migrations import run_migrations
from all_togetharr.platform.secrets import SecretBox, load_or_create_key
from all_togetharr.platform.settings import Settings
from all_togetharr.platform.settings_routes import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(app.state.settings)
    run_migrations(app.state.engine)
    app.state.secret_box = SecretBox(
        load_or_create_key(app.state.settings.config_dir)
    )
    runner = app.state.job_runner
    runner.recover()
    runner.start()
    yield
    runner.stop()
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
    app.state.job_runner = JobRunner(session_factory)

    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(auth_router)
    app.include_router(settings_router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        try:
            return JSONResponse(
                status_code=422,
                content={"detail": exc.errors()},
            )
        except UnicodeEncodeError:
            return JSONResponse(
                status_code=422,
                content={"detail": "Invalid input"},
            )

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
