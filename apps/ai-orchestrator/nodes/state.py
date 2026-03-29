from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_REPLY = "waiting_for_reply"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderQuery(BaseModel):
    order_id: str
    platform: str
    user_question: str


class SuggestionRequest(BaseModel):
    order_id: str
    platform: str
    order_status: str
    user_message: str


class RuleCheckRequest(BaseModel):
    order_id: str
    platform: str
    action: str
    context: Dict[str, Any]


class OrchestratorState(BaseModel):
    status: AgentStatus = AgentStatus.IDLE
    current_order_id: Optional[str] = None
    current_platform: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None
    unified_order: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
    selected_action: Optional[str] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    next_node: Optional[Literal["suggestion", "rule_check", "end"]] = None

    class Config:
        use_enum_values = True
