"""Serve a built SPA as a catch-all route on the API server."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Register a catch-all route that serves the SPA fallback to index.html.

    The route lives at ``/{path:path}`` so it sits alongside the /api/* routes.
    It intentionally returns 404 for paths starting with ``api`` so that the
    FastAPI JSON-404 machinery handles unknown API endpoints.
    """

    root = static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa_handler(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        try:
            candidate = (root / path).resolve()
            if not candidate.is_relative_to(root):
                raise HTTPException(status_code=404, detail="Not Found")
            if candidate.is_file():
                return FileResponse(candidate)
        except (ValueError, OSError):
            raise HTTPException(status_code=404, detail="Not Found") from None

        last_segment = path.rstrip("/").rsplit("/", 1)[-1]
        if "." in last_segment:
            raise HTTPException(status_code=404, detail="Not Found")

        return FileResponse(
            root / "index.html",
            headers={"Cache-Control": "no-cache"},
        )
