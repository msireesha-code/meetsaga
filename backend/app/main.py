from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging

configure_logging()

from app.api import (  # noqa: E402
    analysis,
    dashboard,
    exports,
    jobs,
    meetings,
    search,
    settings_api,
    system,
    transcripts,
)

settings = get_settings()

app = FastAPI(title="MeetSage", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    from app.workers.job_runner import recover_orphaned_jobs

    recover_orphaned_jobs()


app.include_router(meetings.router)
app.include_router(jobs.router)
app.include_router(transcripts.router)
app.include_router(analysis.router)
app.include_router(settings_api.router)
app.include_router(system.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(exports.router)

# --- Production static frontend serving (optional) ---
# When frontend/dist exists (built via `npm run build` / scripts/build_frontend.sh),
# the backend serves it directly on the same origin — no separate vite dev server
# or CORS needed. In local dev (no dist/), the frontend runs its own dev server on
# :5173 and this whole block is skipped; GET "/" falls back to a simple status JSON.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    _ASSETS_DIR = _FRONTEND_DIST / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serves the built SPA, falling back to index.html for client-side
        routes (e.g. /meetings/abc123) that don't correspond to a real file."""
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    def root():
        return {
            "app": "MeetSage",
            "status": "running",
            "note": "frontend/dist not found — run the Vite dev server, or "
            "scripts/build_frontend.sh for production-style same-origin serving.",
        }
