from fastapi import APIRouter

from app.api.routes import runs
from app.api.routes import integration

api_router = APIRouter()

api_router.include_router(runs.router, prefix="/official-sim/runs", tags=["runs"])
api_router.include_router(integration.router, prefix="/official-sim", tags=["integration"])
