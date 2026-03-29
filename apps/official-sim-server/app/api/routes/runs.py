from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

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


@router.post("", response_model=RunCreateResponse, status_code=201)
async def create_run(request: RunCreateRequest):
    run_id = str(uuid.uuid4())
    run_code = f"run_{run_id[:8]}"

    response = RunCreateResponse(
        run_id=run_id,
        run_code=run_code,
        platform=request.platform,
        scenario_name=request.scenario_name,
        status="created",
        current_step=0,
        created_at=datetime.utcnow()
    )

    return response
