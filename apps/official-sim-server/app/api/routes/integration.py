from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
import uuid

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.run_repo import RunRepository
from app.repositories.artifact_repo import ArtifactRepository
from app.repositories.push_event_repo import PushEventRepository
from app.integration.adapter import IntegrationAdapter


router = APIRouter()


class UnifiedRunRequest(BaseModel):
    platform: str
    scenario_name: Optional[str] = None


class UnifiedRunResponse(BaseModel):
    run_id: str
    platform: str
    orders: List[Dict[str, Any]]
    conversations: List[Dict[str, Any]]
    push_events: List[Dict[str, Any]]


@router.post("/unified/run", response_model=UnifiedRunResponse)
async def create_unified_run(
    request: UnifiedRunRequest,
    db: Session = Depends(get_db),
):
    adapter = IntegrationAdapter()
    run_repo = RunRepository(db)
    artifact_repo = ArtifactRepository(db)
    push_repo = PushEventRepository(db)

    run = run_repo.create(
        platform=request.platform,
        run_code=f"unified_{uuid.uuid4().hex[:8]}",
        strict_mode=True,
        push_enabled=True,
    )

    artifacts = artifact_repo.list_by_run(run.id)
    pushes = push_repo.list_by_run(run.id)

    artifacts_data = [
        {
            "id": str(a.id),
            "artifact_type": a.artifact_type.value,
            "platform": a.platform,
            "route_key": a.route_key,
            "response_body_json": a.response_body_json,
        }
        for a in artifacts
    ]

    pushes_data = [
        {
            "id": str(p.id),
            "event_type": p.event_type,
            "platform": p.platform,
            "body_json": p.body_json,
            "status": p.status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in pushes
    ]

    unified_data = adapter.adapt_run_to_unified(
        run_id=run.id,
        platform=run.platform,
        artifacts=artifacts_data,
        pushes=pushes_data,
    )

    return UnifiedRunResponse(**unified_data)


@router.get("/unified/runs/{run_id}")
async def get_unified_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    adapter = IntegrationAdapter()
    run_repo = RunRepository(db)
    artifact_repo = ArtifactRepository(db)
    push_repo = PushEventRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        return {"error": "Run not found"}

    artifacts = artifact_repo.list_by_run(run.id)
    pushes = push_repo.list_by_run(run.id)

    artifacts_data = [
        {
            "id": str(a.id),
            "artifact_type": a.artifact_type.value,
            "platform": a.platform,
            "route_key": a.route_key,
            "response_body_json": a.response_body_json,
        }
        for a in artifacts
    ]

    pushes_data = [
        {
            "id": str(p.id),
            "event_type": p.event_type,
            "platform": p.platform,
            "body_json": p.body_json,
            "status": p.status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in pushes
    ]

    unified_data = adapter.adapt_run_to_unified(
        run_id=run.id,
        platform=run.platform,
        artifacts=artifacts_data,
        pushes=pushes_data,
    )

    return unified_data
