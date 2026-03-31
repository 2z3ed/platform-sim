from fastapi import APIRouter

from app.api.routes import runs
from app.api.routes import integration
from app.api.routes import query

api_router = APIRouter()

api_router.include_router(runs.router, prefix="/official-sim/runs", tags=["runs"])
api_router.include_router(integration.router, prefix="/official-sim", tags=["integration"])
api_router.include_router(query.router, prefix="/official-sim/query", tags=["query"])
