from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class TurnStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED = "ended"


class EmotionType(str, Enum):
    CALM = "calm"
    IMPATIENT = "impatient"
    ANGRY = "angry"
    SATISFIED = "satisfied"


class IntentType(str, Enum):
    ASK_ORDER_STATUS = "ask_order_status"
    ASK_SHIPMENT = "ask_shipment"
    ASK_REFUND = "ask_refund"
    COMPLAIN = "complain"
    PRODUCT_QUESTION = "product_question"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    EMOTION_UPGRADE = "emotion_upgrade"
    THANK = "thank"
    CLOSE = "close"


class ErrorType(str, Enum):
    TOKEN_EXPIRED = "token_expired"
    INVALID_SIGNATURE = "invalid_signature"
    TIMESTAMP_OUT_OF_WINDOW = "timestamp_out_of_window"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RATE_LIMITED = "rate_limited"
    DUPLICATE_PUSH = "duplicate_push"
    OUT_OF_ORDER_PUSH = "out_of_order_push"
    CALLBACK_ACK_INVALID = "callback_ack_invalid"
    CONVERSATION_CLOSED = "conversation_closed"
    MSG_CODE_EXPIRED = "msg_code_expired"


class Message(BaseModel):
    role: str
    content: str
    intent: Optional[str] = None
    emotion: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ToolCallResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    success: bool = True


class TurnContext(BaseModel):
    turn_no: int
    user_message: Optional[Message] = None
    reply_message: Optional[Message] = None
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    emotion: EmotionType = EmotionType.CALM
    intent: Optional[IntentType] = None
    should_continue: bool = True
    status: TurnStatus = TurnStatus.IN_PROGRESS


class ConversationContext(BaseModel):
    run_id: str
    platform: str
    user_id: str
    order_id: str
    conversation_id: str
    scenario_name: str

    current_turn: int = 0
    max_turns: int = 5

    emotion: EmotionType = EmotionType.CALM
    intent: Optional[IntentType] = None

    conversation_history: List[Message] = Field(default_factory=list)
    turn_contexts: List[TurnContext] = Field(default_factory=list)

    tool_results: List[Dict[str, Any]] = Field(default_factory=list)

    status: str = "created"
    end_reason: Optional[str] = None

    unresolved_turns: int = 0
    consecutive_unsatisfied: int = 0
    emotion_escalation_enabled: bool = True
    last_intent: Optional[str] = None
    escalation_to_human: bool = False
    escalation_reason: Optional[str] = None
    error_injection_enabled: bool = False
    injected_error: Optional[ErrorType] = None
    error_count: int = 0
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def add_user_message(self, content: str, intent: str = None, emotion: str = None):
        msg = Message(role="user", content=content, intent=intent, emotion=emotion)
        self.conversation_history.append(msg)

        if self.current_turn >= len(self.turn_contexts):
            self.turn_contexts.append(TurnContext(turn_no=self.current_turn + 1))

        self.turn_contexts[-1].user_message = msg
        self.turn_contexts[-1].emotion = EmotionType(emotion) if emotion else self.emotion
        self.turn_contexts[-1].intent = IntentType(intent) if intent else self.intent
        self.updated_at = datetime.now().isoformat()

    def add_reply_message(self, content: str, source: str = "stub"):
        msg = Message(role="agent", content=content)
        self.conversation_history.append(msg)

        if self.turn_contexts:
            self.turn_contexts[-1].reply_message = msg
        self.updated_at = datetime.now().isoformat()

    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]):
        tool_result = ToolCallResult(
            tool_name=tool_name,
            arguments=arguments,
            result=result
        )
        if self.turn_contexts:
            self.turn_contexts[-1].tool_calls.append(tool_result)
        self.tool_results.append({
            "turn": self.current_turn,
            "tool": tool_name,
            "args": arguments,
            "result": result
        })
        self.updated_at = datetime.now().isoformat()

    def next_turn(self):
        self.current_turn += 1
        if self.current_turn >= self.max_turns:
            self.end_reason = "max_turns_reached"
            self.status = "ended"
        self.updated_at = datetime.now().isoformat()

    def should_continue(self) -> bool:
        if self.status == "ended":
            return False
        if self.current_turn >= self.max_turns:
            return False
        return True

    def escalate_emotion(self, reply_satisfactory: bool = False, current_intent: str = None) -> EmotionType:
        if not self.emotion_escalation_enabled:
            return self.emotion

        if current_intent and self.last_intent and current_intent != self.last_intent:
            self.consecutive_unsatisfied = 0

        if reply_satisfactory:
            if self.emotion == EmotionType.IMPATIENT:
                self.emotion = EmotionType.CALM
            elif self.emotion == EmotionType.ANGRY:
                self.emotion = EmotionType.IMPATIENT
            self.consecutive_unsatisfied = 0
            return self.emotion

        self.consecutive_unsatisfied += 1

        if self.consecutive_unsatisfied >= 2:
            if self.emotion == EmotionType.CALM:
                self.emotion = EmotionType.IMPATIENT
            elif self.emotion == EmotionType.IMPATIENT:
                self.emotion = EmotionType.ANGRY
                self.end_reason = "emotion_escalated_to_angry"
                self.status = "ended"
            self.consecutive_unsatisfied = 0

        return self.emotion

    def is_intent_repeated(self, current_intent: str) -> bool:
        if not self.last_intent:
            return False
        return self.last_intent == current_intent and self.consecutive_unsatisfied > 0

    def get_repeated_count(self, current_intent: str) -> int:
        if not self.last_intent or self.last_intent != current_intent:
            return 0
        return self.consecutive_unsatisfied + 1

    def update_last_intent(self, intent: str):
        self.last_intent = intent

    def end(self, reason: str = "completed"):
        self.status = "ended"
        self.end_reason = reason
        for tc in self.turn_contexts:
            tc.status = TurnStatus.COMPLETED
        self.updated_at = datetime.now().isoformat()

    def enable_error_injection(self, error_type: ErrorType = None):
        self.error_injection_enabled = True
        if error_type:
            self.injected_error = error_type

    def disable_error_injection(self):
        self.error_injection_enabled = False
        self.injected_error = None

    def should_inject_error(self) -> bool:
        return self.error_injection_enabled and self.injected_error is not None

    def inject_error_response(self) -> Dict[str, Any]:
        if not self.should_inject_error():
            return {}
        self.error_count += 1
        error_type = self.injected_error
        error_responses = {
            ErrorType.TOKEN_EXPIRED: {"code": "token_expired", "message": "Token已过期，请重新获取", "retryable": True},
            ErrorType.INVALID_SIGNATURE: {"code": "invalid_signature", "message": "签名验证失败", "retryable": False},
            ErrorType.TIMESTAMP_OUT_OF_WINDOW: {"code": "timestamp_out_of_window", "message": "请求时间戳超出允许范围", "retryable": True},
            ErrorType.PERMISSION_DENIED: {"code": "permission_denied", "message": "无权访问该资源", "retryable": False},
            ErrorType.RESOURCE_NOT_FOUND: {"code": "resource_not_found", "message": "资源不存在", "retryable": False},
            ErrorType.RATE_LIMITED: {"code": "rate_limited", "message": "请求过于频繁，请稍后重试", "retryable": True},
            ErrorType.DUPLICATE_PUSH: {"code": "duplicate_push", "message": "重复的推送请求", "retryable": False},
            ErrorType.OUT_OF_ORDER_PUSH: {"code": "out_of_order_push", "message": "推送顺序错误", "retryable": False},
            ErrorType.CALLBACK_ACK_INVALID: {"code": "callback_ack_invalid", "message": "回调确认无效", "retryable": True},
            ErrorType.CONVERSATION_CLOSED: {"code": "conversation_closed", "message": "会话已关闭", "retryable": False},
            ErrorType.MSG_CODE_EXPIRED: {"code": "msg_code_expired", "message": "消息码已过期", "retryable": True},
        }
        return error_responses.get(error_type, {"code": "unknown_error", "message": "未知错误", "retryable": False})

    def get_recent_messages(self, count: int = 3) -> List[Message]:
        return self.conversation_history[-count:] if self.conversation_history else []

    def get_current_facts(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "current_emotion": self.emotion.value,
            "current_intent": self.intent.value if self.intent else None,
            "conversation_length": len(self.conversation_history),
            "status": self.status,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "platform": self.platform,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "conversation_id": self.conversation_id,
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "status": self.status,
            "end_reason": self.end_reason,
            "total_messages": len(self.conversation_history),
            "escalation_to_human": self.escalation_to_human,
            "escalation_reason": self.escalation_reason,
            "error_injection_enabled": self.error_injection_enabled,
            "injected_error": self.injected_error.value if self.injected_error else None,
            "error_count": self.error_count,
            "artifacts_count": len(self.artifacts),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_artifact(self, artifact_type: str, data: Dict[str, Any]):
        artifact = {
            "artifact_id": f"art_{self.run_id}_{len(self.artifacts) + 1}",
            "artifact_type": artifact_type,
            "turn_no": self.current_turn,
            "data": data,
            "created_at": datetime.now().isoformat(),
        }
        self.artifacts.append(artifact)

    def get_artifacts(self) -> List[Dict[str, Any]]:
        return self.artifacts

    def to_report(self) -> Dict[str, Any]:
        intent_counts: Dict[str, int] = {}
        emotion_changes: List[str] = []
        for tc in self.turn_contexts:
            if tc.intent:
                intent_key = tc.intent.value if hasattr(tc.intent, 'value') else str(tc.intent)
                intent_counts[intent_key] = intent_counts.get(intent_key, 0) + 1
            emotion_changes.append(tc.emotion.value if hasattr(tc.emotion, 'value') else str(tc.emotion))

        return {
            "run_id": self.run_id,
            "platform": self.platform,
            "scenario_name": self.scenario_name,
            "status": self.status,
            "end_reason": self.end_reason,
            "summary": {
                "turns": self.current_turn,
                "final_emotion": self.emotion.value if hasattr(self.emotion, 'value') else str(self.emotion),
                "intent_distribution": intent_counts,
                "emotion_changes": emotion_changes,
            },
            "escalation": {
                "escalated_to_human": self.escalation_to_human,
                "reason": self.escalation_reason,
            },
            "errors": {
                "error_injection_enabled": self.error_injection_enabled,
                "injected_error": self.injected_error.value if self.injected_error else None,
                "error_count": self.error_count,
            },
            "artifacts_count": len(self.artifacts),
            "open_issues": [],
            "injected_errors": [e for e in self.artifacts if e.get("artifact_type") == "error_injection"],
            "observed_errors": [],
        }
