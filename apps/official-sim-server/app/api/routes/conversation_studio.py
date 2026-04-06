"""Conversation Studio API routes.

Provides a minimal bridge between the domain-service's conversation flow
and the official-sim run lifecycle.

Endpoints:
  POST /conversation-studio/runs            - create a new conversation run
  POST /conversation-studio/runs/{run_id}/agent-message - send agent message, get user reply
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
import uuid
import random

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.run_repo import RunRepository
from app.repositories.event_repo import EventRepository
from app.models.models import RunStatus

router = APIRouter()

SCENE_STATES = {
    "pending_ship": {
        "description": "订单未发货，客户可能在问发货时间/物流单号",
        "shipped": False,
        "has_tracking": False,
    },
    "shipped_no_tracking": {
        "description": "已发货但暂无物流单号",
        "shipped": True,
        "has_tracking": False,
    },
    "shipped_with_tracking": {
        "description": "已发货且有物流单号",
        "shipped": True,
        "has_tracking": True,
    },
    "after_sale_processing": {
        "description": "售后处理中",
        "shipped": False,
        "has_tracking": False,
    },
}

_SCENE_FILTERED_REPLIES = {
    "pending_ship": {
        "positive": [
            "好的，谢谢",
            "好的，我再等等看",
            "好的，知道了",
            "好的，麻烦你了",
        ],
        "eta_related": [
            "那大概什么时候能发呢？",
            "大概多久能发？",
            "能帮我催一下尽快发吗？",
            "什么时候可以发？",
        ],
        "tracking_related": [
            "请问有物流单号吗？",
            "有单号了吗？",
            "什么时候有单号？",
        ],
    },
    "shipped_no_tracking": {
        "positive": [
            "好的，谢谢",
            "好的，我再等等看",
            "好的，知道了",
        ],
        "eta_related": [
            "那大概什么时候能到呢？",
            "大概几天能到？",
            "大概多久能到？",
        ],
        "tracking_related": [
            "请问有物流单号吗？",
            "有单号了吗？",
        ],
    },
    "shipped_with_tracking": {
        "positive": [
            "好的，谢谢",
            "好的，我再等等看",
            "好的，知道了",
        ],
        "eta_related": [
            "那大概什么时候能到呢？",
            "大概几天能到？",
        ],
        "tracking_related": [
            "请问有物流单号吗？",
        ],
    },
    "default": {
        "positive": [
            "好的，谢谢",
            "好的，我再等等看",
            "好的，知道了",
            "好的，麻烦你了",
        ],
        "eta_related": [
            "那大概什么时候能到呢？",
            "大概几天能到？",
            "大概多久能到？",
            "什么时候可以发？",
        ],
        "tracking_related": [
            "请问有物流单号吗？",
            "有单号了吗？",
        ],
    },
}

_REPEAT_WARNING_PHRASES = [
    "请耐心等待",
    "后续有消息会通知您",
    "有问题随时联系我",
    "我会第一时间通知您",
    "请放心等待",
]


class StudioRunCreateRequest(BaseModel):
    platform: str = Field(..., description="Platform code")
    conversation_id: str = Field(..., description="Conversation identifier")
    scenario_name: str = Field(default="default", description="Scenario template")
    max_turns: int = Field(default=100, description="Maximum conversation turns")
    scene_state: str = Field(default="pending_ship", description="Local scene state for facts consistency")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StudioRunCreateResponse(BaseModel):
    run_id: str
    platform: str
    conversation_id: str
    status: str


class AgentMessageRequest(BaseModel):
    agent_message: str = Field(..., description="Agent reply content")
    conversation_id: str = Field(..., description="Conversation identifier")


class AgentMessageResponse(BaseModel):
    user_message: str
    run_id: str
    turn_no: int


def _get_question_intent(agent_message: str) -> str:
    """Detect what question type the user's last message is about."""
    msg = agent_message.lower()
    
    if any(kw in msg for kw in ["发", "发货", "什么时候发", "多久发", "催"]):
        return "eta_related"
    if any(kw in msg for kw in ["单号", "物流", "到了", "到哪", "什么时候到", "几天"]):
        return "tracking_related"
    if any(kw in msg for kw in ["通知", "回复", "消息"]):
        return "notification_related"
    
    return "positive"


def _filter_by_repetition(candidates: List[str], last_reply: str, step: int) -> str:
    """Filter out candidates that repeat too closely with last reply."""
    if not last_reply:
        return random.choice(candidates)
    
    filtered = [c for c in candidates if c != last_reply]
    if not filtered:
        return candidates[step % len(candidates)]
    
    return random.choice(filtered)


def _generate_user_reply(
    scene_state: str,
    agent_message: str,
    current_step: int,
    last_reply: str,
    last_user_intent: str,
) -> str:
    """Generate user reply with facts consistency, current-question-first, and anti-repetition."""
    
    scene_templates = _SCENE_FILTERED_REPLIES.get(scene_state, _SCENE_FILTERED_REPLIES["default"])
    
    question_intent = last_user_intent if last_user_intent else "eta_related"
    
    if question_intent in scene_templates and scene_templates[question_intent]:
        candidates = scene_templates[question_intent]
        selected = _filter_by_repetition(candidates, last_reply, current_step)
        return selected
    
    if last_user_intent in scene_templates and scene_templates[last_user_intent]:
        candidates = scene_templates[last_user_intent]
        selected = _filter_by_repetition(candidates, last_reply, current_step)
        return selected
    
    candidates = scene_templates.get("positive", ["好的，谢谢"])
    selected = _filter_by_repetition(candidates, last_reply, current_step)
    return selected


@router.post("/runs", response_model=StudioRunCreateResponse, status_code=201)
async def create_studio_run(
    request: StudioRunCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new conversation studio run."""
    repo = RunRepository(db)
    run_code = f"studio_{uuid.uuid4().hex[:8]}"

    metadata = dict(request.metadata or {})
    metadata["scenario_name"] = request.scenario_name
    metadata["conversation_id"] = request.conversation_id
    metadata["max_turns"] = request.max_turns
    metadata["scene_state"] = request.scene_state

    run = repo.create(
        platform=request.platform,
        run_code=run_code,
        strict_mode=False,
        push_enabled=False,
        seed=None,
        metadata=metadata,
    )

    return StudioRunCreateResponse(
        run_id=str(run.id),
        platform=request.platform,
        conversation_id=request.conversation_id,
        status="created",
    )


@router.post("/runs/{run_id}/agent-message", response_model=AgentMessageResponse)
async def agent_message(
    run_id: UUID,
    request: AgentMessageRequest,
    db: Session = Depends(get_db),
):
    """Process an agent message and return a simulated user reply."""
    run_repo = RunRepository(db)
    event_repo = EventRepository(db)

    run = run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run_repo.update_status(run.id, RunStatus.RUNNING)

    run_repo.advance_step(run.id)
    db.refresh(run)
    current_step = run.current_step

    last_reply = run.metadata_json.get("last_user_reply", "") if run.metadata_json else ""
    last_user_intent = run.metadata_json.get("last_user_intent", "positive") if run.metadata_json else "positive"
    scene_state = run.metadata_json.get("scene_state", "pending_ship") if run.metadata_json else "pending_ship"

    user_message = _generate_user_reply(
        scene_state=scene_state,
        agent_message=request.agent_message,
        current_step=current_step,
        last_reply=last_reply,
        last_user_intent=last_user_intent,
    )

    question_intent = _get_question_intent(request.agent_message)

    if run.metadata_json is None:
        run.metadata_json = {}
    run.metadata_json["last_user_reply"] = user_message
    run.metadata_json["last_user_intent"] = question_intent
    db.commit()

    event_repo.create(
        run_id=run.id,
        step_no=current_step,
        event_type="agent_message",
        source_type="domain_service",
        payload={
            "agent_message": request.agent_message,
            "conversation_id": request.conversation_id,
        },
    )

    return AgentMessageResponse(
        user_message=user_message,
        run_id=str(run.id),
        turn_no=current_step,
    )
