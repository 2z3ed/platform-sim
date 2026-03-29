from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
import uuid

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.run_repo import RunRepository
from app.repositories.event_repo import EventRepository
from app.repositories.snapshot_repo import SnapshotRepository
from app.repositories.artifact_repo import ArtifactRepository
from app.repositories.push_event_repo import PushEventRepository
from app.models.models import RunStatus
from app.core.errors import ErrorCode, get_error_response
from app.domain.scenario_engine import ScenarioEngine

router = APIRouter()


class RunCreateRequest(BaseModel):
    platform: str = Field(..., description="Platform: taobao, douyin_shop, wecom_kf, jd, xhs, kuaishou")
    scenario_name: str = Field(..., min_length=1, description="Scenario template name")
    strict_mode: bool = Field(default=True, description="Enable strict state machine validation")
    push_enabled: bool = Field(default=True, description="Enable push event generation")
    account_code: Optional[str] = Field(default=None, description="Platform account code")
    seed: Optional[str] = Field(default=None, description="Random seed for deterministic execution")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class RunCreateResponse(BaseModel):
    run_id: str
    run_code: str
    platform: str
    scenario_name: str
    status: str
    current_step: int
    created_at: datetime


class RunGetResponse(BaseModel):
    run_id: str
    run_code: str
    platform: str
    status: str
    current_step: int
    strict_mode: bool
    push_enabled: bool
    seed: Optional[str]
    metadata: Dict[str, Any]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RunAdvanceRequest(BaseModel):
    next_step: Optional[int] = Field(default=None, description="Optional explicit next step number")
    event_type: str = Field(default="step_advance", description="Event type for this advance")


class RunAdvanceResponse(BaseModel):
    run_id: str
    run_code: str
    previous_step: int
    current_step: int
    status: str
    message: str
    event_id: str


class EventResponse(BaseModel):
    event_id: str
    run_id: str
    step_no: int
    event_type: str
    source_type: Optional[str]
    payload: Dict[str, Any]
    created_at: datetime


class SnapshotResponse(BaseModel):
    snapshot_id: str
    run_id: str
    step_no: int
    auth_state: Dict[str, Any]
    order_state: Dict[str, Any]
    shipment_state: Dict[str, Any]
    after_sale_state: Dict[str, Any]
    conversation_state: Dict[str, Any]
    push_state: Dict[str, Any]
    created_at: datetime


@router.post("", response_model=RunCreateResponse, status_code=201)
async def create_run(
    request: RunCreateRequest,
    db: Session = Depends(get_db),
):
    repo = RunRepository(db)
    run_code = f"run_{uuid.uuid4().hex[:8]}"

    metadata = dict(request.metadata or {})
    metadata["scenario_name"] = request.scenario_name

    run = repo.create(
        platform=request.platform,
        run_code=run_code,
        strict_mode=request.strict_mode,
        push_enabled=request.push_enabled,
        seed=request.seed,
        metadata=metadata,
    )

    return RunCreateResponse(
        run_id=str(run.id),
        run_code=run.run_code,
        platform=run.platform,
        scenario_name=request.scenario_name,
        status=run.status.value,
        current_step=run.current_step,
        created_at=run.created_at,
    )


@router.get("/{run_id}", response_model=RunGetResponse)
async def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    repo = RunRepository(db)
    run = repo.get_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunGetResponse(
        run_id=str(run.id),
        run_code=run.run_code,
        platform=run.platform,
        status=run.status.value,
        current_step=run.current_step,
        strict_mode=run.strict_mode == "1",
        push_enabled=run.push_enabled == "1",
        seed=run.seed,
        metadata=run.metadata_json or {},
        started_at=run.started_at,
        ended_at=run.ended_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/{run_id}/advance", response_model=RunAdvanceResponse)
async def advance_run(
    run_id: UUID,
    request: RunAdvanceRequest,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    event_repo = EventRepository(db)
    snapshot_repo = SnapshotRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in (RunStatus.CREATED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance run in status: {run.status.value}",
        )

    previous_step = run.current_step

    if run.status == RunStatus.CREATED:
        run_repo.update_status(run.id, RunStatus.RUNNING)
        run.status = RunStatus.RUNNING

    run_repo.advance_step(run.id)
    new_step = run.current_step

    event = event_repo.create(
        run_id=run.id,
        step_no=new_step,
        event_type=request.event_type,
        source_type="run_advance",
        payload={"previous_step": previous_step, "new_step": new_step},
    )

    scenario_engine = ScenarioEngine(db)
    scenario_result = scenario_engine.execute_step(
        run_id=run.id,
        platform=run.platform,
        scenario_name=run.metadata_json.get("scenario_name", "wait_ship_basic"),
        current_step=new_step - 1,
    )

    snapshot_state = {
        "auth_state": {"platform": run.platform, "step": new_step},
        "order_state": {"status": scenario_result.get("next_status", "initial")},
        "shipment_state": {"status": "initial"},
        "after_sale_state": {"status": "no_refund"},
        "conversation_state": {"status": "initial"},
        "push_state": {"pushed": []},
    }

    if scenario_result.get("pushes_created", 0) > 0:
        push_repo = PushEventRepository(db)
        pushes = push_repo.list_by_run_and_step(run.id, new_step)
        snapshot_state["push_state"]["pushed"] = [str(p.id) for p in pushes]

    snapshot_repo.create(
        run_id=run.id,
        step_no=new_step,
        **snapshot_state,
    )

    artifact_repo = ArtifactRepository(db)
    artifact_repo.create(
        run_id=run.id,
        step_no=new_step,
        platform=run.platform,
        artifact_type="api_response_snapshot",
        route_key=f"/advance/step_{new_step}",
        request_headers={},
        request_body={"step": new_step},
        response_headers={"content-type": "application/json"},
        response_body={
            "status": "success",
            "step": new_step,
            "message": f"Advanced to step {new_step}",
        },
    )

    return RunAdvanceResponse(
        run_id=str(run.id),
        run_code=run.run_code,
        previous_step=previous_step,
        current_step=new_step,
        status=run.status.value,
        message=f"Advanced from step {previous_step} to {new_step}",
        event_id=str(event.id),
    )


@router.get("/{run_id}/events", response_model=List[EventResponse])
async def list_events(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    event_repo = EventRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    events = event_repo.list_by_run(run_id)

    return [
        EventResponse(
            event_id=str(e.id),
            run_id=str(e.run_id),
            step_no=e.step_no,
            event_type=e.event_type,
            source_type=e.source_type,
            payload=e.payload_json or {},
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/{run_id}/snapshots", response_model=List[SnapshotResponse])
async def list_snapshots(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    snapshot_repo = SnapshotRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    snapshots = snapshot_repo.list_by_run(run_id)

    return [
        SnapshotResponse(
            snapshot_id=str(s.id),
            run_id=str(s.run_id),
            step_no=s.step_no,
            auth_state=s.auth_state_json or {},
            order_state=s.order_state_json or {},
            shipment_state=s.shipment_state_json or {},
            after_sale_state=s.after_sale_state_json or {},
            conversation_state=s.conversation_state_json or {},
            push_state=s.push_state_json or {},
            created_at=s.created_at,
        )
        for s in snapshots
    ]


class ArtifactResponse(BaseModel):
    artifact_id: str
    run_id: str
    step_no: int
    platform: str
    artifact_type: str
    route_key: Optional[str]
    request_headers: Dict[str, Any]
    request_body: Dict[str, Any]
    response_headers: Dict[str, Any]
    response_body: Dict[str, Any]
    created_at: datetime


@router.get("/{run_id}/artifacts", response_model=List[ArtifactResponse])
async def list_artifacts(
    run_id: UUID,
    step_no: Optional[int] = None,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    artifact_repo = ArtifactRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if step_no is not None:
        artifacts = artifact_repo.list_by_run_and_step(run_id, step_no)
    else:
        artifacts = artifact_repo.list_by_run(run_id)

    return [
        ArtifactResponse(
            artifact_id=str(a.id),
            run_id=str(a.run_id),
            step_no=a.step_no,
            platform=a.platform,
            artifact_type=a.artifact_type.value,
            route_key=a.route_key,
            request_headers=a.request_headers_json or {},
            request_body=a.request_body_json or {},
            response_headers=a.response_headers_json or {},
            response_body=a.response_body_json or {},
            created_at=a.created_at,
        )
        for a in artifacts
    ]


class PushEventResponse(BaseModel):
    push_id: str
    run_id: str
    step_no: int
    platform: str
    event_type: str
    status: str
    headers: Dict[str, Any]
    body: Dict[str, Any]
    sent_at: Optional[datetime]
    acked_at: Optional[datetime]
    retry_count: int
    created_at: datetime


@router.get("/{run_id}/pushes", response_model=List[PushEventResponse])
async def list_pushes(
    run_id: UUID,
    step_no: Optional[int] = None,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    push_repo = PushEventRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if step_no is not None:
        pushes = push_repo.list_by_run_and_step(run_id, step_no)
    else:
        pushes = push_repo.list_by_run(run_id)

    return [
        PushEventResponse(
            push_id=str(p.id),
            run_id=str(p.run_id),
            step_no=p.step_no,
            platform=p.platform,
            event_type=p.event_type,
            status=p.status.value,
            headers=p.headers_json or {},
            body=p.body_json or {},
            sent_at=p.sent_at,
            acked_at=p.acked_at,
            retry_count=p.retry_count,
            created_at=p.created_at,
        )
        for p in pushes
    ]


class ReplayPushRequest(BaseModel):
    push_id: str


class ReplayPushResponse(BaseModel):
    original_push_id: str
    new_push_id: str
    run_id: str
    step_no: int
    platform: str
    event_type: str
    status: str
    message: str


@router.post("/{run_id}/replay-push", response_model=ReplayPushResponse)
async def replay_push(
    run_id: UUID,
    request: ReplayPushRequest,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    push_repo = PushEventRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    original_push = push_repo.get_by_id(UUID(request.push_id))
    if not original_push:
        raise HTTPException(status_code=404, detail="Push event not found")

    if original_push.run_id != run_id:
        raise HTTPException(status_code=400, detail="Push event does not belong to this run")

    new_push = push_repo.create_from_replay(original_push)

    return ReplayPushResponse(
        original_push_id=str(original_push.id),
        new_push_id=str(new_push.id),
        run_id=str(new_push.run_id),
        step_no=new_push.step_no,
        platform=new_push.platform,
        event_type=new_push.event_type,
        status=new_push.status.value,
        message=f"Replayed push event from step {new_push.step_no}",
    )


class InjectErrorRequest(BaseModel):
    error_code: str
    route_key: Optional[str] = None


class InjectErrorResponse(BaseModel):
    run_id: str
    step_no: int
    error_code: str
    message: str
    http_status: int
    retryable: bool
    artifact_id: str


@router.post("/{run_id}/inject-error", response_model=InjectErrorResponse)
async def inject_error(
    run_id: UUID,
    request: InjectErrorRequest,
    db: Session = Depends(get_db),
):
    run_repo = RunRepository(db)
    artifact_repo = ArtifactRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        error_code = ErrorCode(request.error_code)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown error code: {request.error_code}")

    error_info = get_error_response(error_code)

    artifact = artifact_repo.create(
        run_id=run.id,
        step_no=run.current_step,
        platform=run.platform,
        artifact_type="error_response_payload",
        route_key=request.route_key,
        request_body={"error_code": request.error_code},
        response_body=error_info,
    )

    return InjectErrorResponse(
        run_id=str(run.id),
        step_no=run.current_step,
        error_code=error_info["error"],
        message=error_info["message"],
        http_status=error_info["http_status"],
        retryable=error_info.get("retryable", False),
        artifact_id=str(artifact.id),
    )
