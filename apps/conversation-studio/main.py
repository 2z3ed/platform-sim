"""Minimal Conversation Studio service.

Provides the two endpoints needed by the domain-service for auto-reply:
  POST /conversation-studio/runs
  POST /conversation-studio/runs/{run_id}/agent-message

This is a lightweight standalone service, not the full official-sim-server.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import os
import random

app = FastAPI(title="Conversation Studio", version="0.1.0")

# In-memory run store (no DB dependency)
RUNS: Dict[str, dict] = {}

# Simplified intent detection from agent message
def _detect_intent(agent_message: str) -> str:
    """Detect user intent based on agent message content."""
    msg = agent_message.lower()
    if any(kw in msg for kw in ["发货", "还没发", "尽快", "安排"]):
        return "ask_ship_time"
    elif any(kw in msg for kw in ["物流", "快递", "单号", "到哪", "运输"]):
        return "ask_logistics"
    elif any(kw in msg for kw in ["退款", "钱到", "到账"]):
        return "ask_refund"
    elif any(kw in msg for kw in ["已发货", "发走了", "快递发出了"]):
        return "confirm_shipped"
    elif any(kw in msg for kw in ["还没", "没有", "暂时"]):
        return "accept_wait"
    return "general_confirm"

# User reply templates by intent (more natural variations)
_USER_REPLIES = {
    # When user accepts waiting - vary the expression
    "accept_wait": [
        "好的，那我先等等",
        "好的，麻烦有消息通知我一下",
        "明白了，有进展麻烦告诉我",
        "行，那我先等着，有消息跟我说一声",
        "好的，麻烦帮我跟进一下",
        "好的，有消息同步我",
    ],
    # When user asks about shipping time
    "ask_ship_time": [
        "大概什么时候能发呢？",
        "能帮我催一下尽快发吗？",
        "请问大概多久能发？",
        "麻烦尽快安排发货，谢谢",
        "什么时候可以发？",
    ],
    # When user asks about logistics/tracking
    "ask_logistics": [
        "请问有物流单号了吗？",
        "帮我查一下物流到哪了",
        "快递到哪了？",
        "有单号了能告诉我一下吗？",
        "麻烦帮我看看物流信息",
    ],
    # When agent confirms shipped
    "confirm_shipped": [
        "好的，麻烦有物流单号了告诉我",
        "好的，帮我关注一下物流",
        "好的，谢谢",
        "那麻烦到货前通知我一下",
        "好的，收到后麻烦告诉我",
    ],
    # When asking about refund
    "ask_refund": [
        "请问退款大概多久能到账？",
        "退款进度能查一下吗？",
        "退款什么时候能到？",
        "帮忙看一下退款进度",
    ],
    # General confirmations (used as fallback, avoid overusing)
    "general_confirm": [
        "好的，麻烦你了",
        "好的，知道了",
        "谢谢",
        "好的，我知道了",
    ],
}


def _should_skip(reply: str, recent_replies: List[str], skip_phrases: List[str]) -> bool:
    """Check if reply should be skipped due to repetition."""
    reply_normalized = reply.replace("好的", "").replace("谢谢", "").replace("，", "").strip()
    for recent in recent_replies:
        recent_normalized = recent.replace("好的", "").replace("谢谢", "").replace("，", "").strip()
        if len(reply_normalized) > 0 and len(recent_normalized) > 0:
            if reply_normalized == recent_normalized:
                return True
    for phrase in skip_phrases:
        if phrase in reply:
            return True
    return False


def _get_reply_for_intent(intent: str, used_replies: List[str], recent_replies: List[str]) -> str:
    """Get a reply based on intent, avoiding repetition."""
    templates = _USER_REPLIES.get(intent, _USER_REPLIES["general_confirm"])
    
    # Filter out recently used replies
    available = [r for r in templates if r not in used_replies]
    if not available:
        available = templates
    
    # Try to find a non-repetitive reply
    for reply in available:
        if not _should_skip(reply, recent_replies, ["好的，谢谢", "好的，知道了"]):
            return reply
    
    # Fallback: random choice from available
    return random.choice(available)


class StudioRunCreateRequest(BaseModel):
    platform: str = Field(..., description="Platform code")
    conversation_id: str = Field(..., description="Conversation identifier")
    scenario_name: str = Field(default="default", description="Scenario template")
    max_turns: int = Field(default=100, description="Maximum conversation turns")
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


@app.post("/conversation-studio/runs", response_model=StudioRunCreateResponse, status_code=201)
async def create_studio_run(request: StudioRunCreateRequest):
    """Create a new conversation studio run."""
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {
        "run_id": run_id,
        "platform": request.platform,
        "conversation_id": request.conversation_id,
        "scenario_name": request.scenario_name,
        "max_turns": request.max_turns,
        "status": "running",
        "turn_no": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    return StudioRunCreateResponse(
        run_id=run_id,
        platform=request.platform,
        conversation_id=request.conversation_id,
        status="running",
    )


@app.post("/conversation-studio/runs/{run_id}/agent-message", response_model=AgentMessageResponse)
async def agent_message(run_id: str, request: AgentMessageRequest):
    """Process an agent message and return a simulated user reply."""
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run["turn_no"] += 1
    turn_no = run["turn_no"]

    # Initialize history if not exists
    if "used_replies" not in run:
        run["used_replies"] = []
    if "recent_replies" not in run:
        run["recent_replies"] = []
    
    used_replies = run["used_replies"]
    recent_replies = run["recent_replies"][-3:]  # Keep last 3 for comparison
    
    # Detect intent from agent message and get appropriate reply
    intent = _detect_intent(request.agent_message)
    user_message = _get_reply_for_intent(intent, used_replies, recent_replies)
    
    # Update history
    used_replies.append(user_message)
    if len(used_replies) > 20:  # Keep last 20
        used_replies.pop(0)
    
    recent_replies.append(user_message)
    if len(recent_replies) > 3:
        recent_replies.pop(0)
    
    run["used_replies"] = used_replies
    run["recent_replies"] = recent_replies

    return AgentMessageResponse(
        user_message=user_message,
        run_id=run_id,
        turn_no=turn_no,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "conversation-studio", "active_runs": len(RUNS)}
