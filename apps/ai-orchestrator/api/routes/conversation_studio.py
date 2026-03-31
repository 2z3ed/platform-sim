from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from nodes.conversation_studio import ConversationStudioGraph
from nodes.conversation import ConversationContext


router = APIRouter(prefix="/conversation-studio", tags=["conversation-studio"])

_studio_instances: Dict[str, ConversationStudioGraph] = {}
_contexts: Dict[str, ConversationContext] = {}


class CreateRunRequest(BaseModel):
    platform: str
    user_id: Optional[str] = None
    order_id: Optional[str] = None
    conversation_id: Optional[str] = None
    scenario_name: str = "default"
    emotion: str = "calm"
    max_turns: int = 5
    use_official_sim: bool = False


class CreateRunResponse(BaseModel):
    run_id: str
    conversation_id: str
    platform: str
    status: str


class NextTurnRequest(BaseModel):
    override_intent: Optional[str] = None
    override_emotion: Optional[str] = None


class NextTurnResponse(BaseModel):
    run_id: str
    turn_no: int
    user_message: str
    reply_message: str
    reply_source: str
    intent: str
    emotion: str
    tool_calls: List[Dict[str, Any]]
    continue_suggested: bool
    escalation_to_human: bool = False
    escalation_reason: Optional[str] = None
    error_injected: bool = False
    error_response: Optional[Dict[str, Any]] = None


class RunSummaryResponse(BaseModel):
    run_id: str
    platform: str
    user_id: str
    order_id: str
    conversation_id: str
    current_turn: int
    max_turns: int
    status: str
    end_reason: Optional[str]
    total_messages: int
    created_at: str
    updated_at: str


class DebugResponse(BaseModel):
    run_id: str
    current_facts: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    reply_adapter_mode: str


class ReportResponse(BaseModel):
    run_id: str
    platform: str
    scenario_name: str
    status: str
    end_reason: Optional[str]
    summary: Dict[str, Any]
    escalation: Dict[str, Any]
    errors: Dict[str, Any]
    artifacts_count: int
    open_issues: List[str]
    injected_errors: List[Dict[str, Any]]
    observed_errors: List[Dict[str, Any]]


@router.post("/runs", response_model=CreateRunResponse)
async def create_run(request: CreateRunRequest):
    studio = ConversationStudioGraph(use_official_sim=request.use_official_sim)
    _studio_instances[request.platform] = studio

    context = studio.create_run(
        platform=request.platform,
        user_id=request.user_id,
        order_id=request.order_id,
        conversation_id=request.conversation_id,
        scenario_name=request.scenario_name,
        emotion=request.emotion,
        max_turns=request.max_turns,
    )

    _contexts[context.run_id] = context

    return CreateRunResponse(
        run_id=context.run_id,
        conversation_id=context.conversation_id,
        platform=context.platform,
        status="created",
    )


@router.post("/runs/{run_id}/next", response_model=NextTurnResponse)
async def next_turn(run_id: str, request: NextTurnRequest = None):
    if run_id not in _contexts:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    context = _contexts[run_id]
    studio = _studio_instances.get(context.platform)

    if not studio:
        raise HTTPException(status_code=500, detail=f"Studio for platform {context.platform} not found")

    override_intent = request.override_intent if request else None
    override_emotion = request.override_emotion if request else None

    turn_output = studio.next_turn(
        context,
        override_intent=override_intent,
        override_emotion=override_emotion,
    )

    return NextTurnResponse(
        run_id=run_id,
        turn_no=turn_output.turn_no,
        user_message=turn_output.user_message,
        reply_message=turn_output.reply_message,
        reply_source=turn_output.reply_source,
        intent=turn_output.intent,
        emotion=turn_output.emotion,
        tool_calls=turn_output.tool_calls,
        continue_suggested=turn_output.continue_suggested,
        escalation_to_human=turn_output.escalation_to_human,
        escalation_reason=turn_output.escalation_reason,
        error_injected=turn_output.error_injected,
        error_response=turn_output.error_response,
    )


@router.get("/runs/{run_id}", response_model=RunSummaryResponse)
async def get_run(run_id: str):
    if run_id not in _contexts:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    context = _contexts[run_id]
    summary = context.to_summary()

    return RunSummaryResponse(**summary)


@router.get("/runs/{run_id}/debug", response_model=DebugResponse)
async def get_debug(run_id: str):
    if run_id not in _contexts:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    context = _contexts[run_id]
    studio = _studio_instances.get(context.platform)

    reply_mode = "unknown"
    if studio:
        modes = studio.reply_adapter.get_available_modes()
        reply_mode = "official-sim" if modes.get("use_official_sim") else "stub"

    return DebugResponse(
        run_id=run_id,
        current_facts=context.get_current_facts(),
        conversation_history=[
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in context.conversation_history
        ],
        tool_results=context.tool_results,
        reply_adapter_mode=reply_mode,
    )


@router.get("/runs/{run_id}/messages")
async def get_messages(run_id: str):
    if run_id not in _contexts:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    context = _contexts[run_id]

    return {
        "run_id": run_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "emotion": m.emotion,
                "timestamp": m.timestamp,
            }
            for m in context.conversation_history
        ],
        "total": len(context.conversation_history),
    }
