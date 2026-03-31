import sys
from pathlib import Path

_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes.conversation_studio import router as conversation_studio_router

app = FastAPI(
    title="AI Orchestrator",
    description="AI Orchestrator for Customer Service Simulation",
    version="0.1.0",
)

app.include_router(conversation_studio_router)

static_dir = _root / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "conversation_studio.html"))


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "ai-orchestrator"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
