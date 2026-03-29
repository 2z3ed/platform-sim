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
from app.models.models import RunStatus

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

    run = repo.create(
        platform=request.platform,
        run_code=run_code,
        strict_mode=request.strict_mode,
        push_enabled=request.push_enabled,
        seed=request.seed,
        metadata=request.metadata,
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

    snapshot_repo.create(
        run_id=run.id,
        step_no=new_step,
        auth_state={"platform": run.platform, "step": new_step},
        order_state={"status": "initial"},
        shipment_state={"status": "initial"},
        after_sale_state={"status": "initial"},
        conversation_state={"status": "initial"},
        push_state={"pushed": []},
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
