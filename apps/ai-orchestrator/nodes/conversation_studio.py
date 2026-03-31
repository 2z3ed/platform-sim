from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum

from nodes.conversation import ConversationContext, EmotionType, IntentType
from nodes.reply import UnifiedReplyAdapter, ReplySource
from nodes.user_simulator import UserSimulator


class StudioStatus(str, Enum):
    IDLE = "idle"
    LOADING_CONTEXT = "loading_context"
    USER_LOOP = "user_loop"
    SYSTEM_LOOP = "system_loop"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionOutput(BaseModel):
    selected_user_id: str
    selected_order_id: str
    intent: str
    emotion: str
    should_continue: bool
    should_call_tools: bool
    tool_calls_planned: List[Dict[str, Any]] = Field(default_factory=list)
    reason: str


class TurnOutput(BaseModel):
    turn_no: int
    user_message: str
    reply_message: str
    reply_source: str
    intent: str
    emotion: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    continue_suggested: bool
    escalation_to_human: bool = False
    escalation_reason: Optional[str] = None
    error_injected: bool = False
    error_response: Optional[Dict[str, Any]] = None


class ConversationStudioGraph:
    def __init__(
        self,
        use_official_sim: bool = False,
        official_sim_url: str = "http://localhost:8000",
        platform: str = "taobao"
    ):
        self.user_simulator = UserSimulator()
        self.reply_adapter = UnifiedReplyAdapter(
            use_official_sim=use_official_sim,
            official_sim_base_url=official_sim_url,
            platform=platform
        )

    def create_run(
        self,
        platform: str,
        user_id: Optional[str] = None,
        order_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        scenario_name: str = "default",
        emotion: str = "calm",
        max_turns: int = 5,
    ) -> ConversationContext:
        import uuid
        run_id = f"cs_run_{uuid.uuid4().hex[:8]}"

        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

        context = ConversationContext(
            run_id=run_id,
            platform=platform,
            user_id=user_id or "",
            order_id=order_id or "",
            conversation_id=conversation_id,
            scenario_name=scenario_name,
            max_turns=max_turns,
            emotion=EmotionType(emotion) if emotion else EmotionType.CALM,
        )

        return context

    def next_turn(
        self,
        context: ConversationContext,
        override_intent: Optional[str] = None,
        override_emotion: Optional[str] = None,
    ) -> TurnOutput:
        context.current_turn += 1

        user_loop_result = self._user_loop(context, override_intent, override_emotion)

        reply_result = self._system_loop(context, user_loop_result["user_message"])

        is_repeated = context.is_intent_repeated(user_loop_result["intent"])
        repeated_count = context.get_repeated_count(user_loop_result["intent"])

        context.update_last_intent(user_loop_result["intent"])

        reply_satisfactory = self._evaluate_reply_quality(reply_result, user_loop_result["intent"])
        context.escalate_emotion(reply_satisfactory=reply_satisfactory, current_intent=user_loop_result["intent"])

        if is_repeated and repeated_count >= 2:
            context.intent = IntentType.EMOTION_UPGRADE

        if context.emotion == EmotionType.ANGRY or context.consecutive_unsatisfied >= 2:
            context.escalation_to_human = True
            context.escalation_reason = "emotion_or_repeated_escalation"
            context.end(reason="escalate_to_human")

        error_response = None
        error_injected = False
        if context.should_inject_error():
            error_injected = True
            error_response = context.inject_error_response()

        turn_output = TurnOutput(
            turn_no=context.current_turn,
            user_message=user_loop_result["user_message"],
            reply_message=reply_result["text"],
            reply_source=reply_result["source"],
            intent=user_loop_result["intent"],
            emotion=context.emotion.value,
            tool_calls=user_loop_result["tool_calls"],
            continue_suggested=context.should_continue(),
            escalation_to_human=context.escalation_to_human,
            escalation_reason=context.escalation_reason,
            error_injected=error_injected,
            error_response=error_response,
        )

        context.add_artifact("conversation_turn", {
            "turn_no": turn_output.turn_no,
            "user_message": turn_output.user_message,
            "reply_message": turn_output.reply_message,
            "intent": turn_output.intent,
            "emotion": turn_output.emotion,
        })

        if error_injected:
            context.add_artifact("error_injection", {
                "turn_no": turn_output.turn_no,
                "error": error_response,
            })

        if context.escalation_to_human:
            context.add_artifact("escalation", {
                "turn_no": turn_output.turn_no,
                "reason": context.escalation_reason,
            })

        return turn_output

    def _evaluate_reply_quality(self, reply_result: Dict[str, Any], intent: str) -> bool:
        reply_text = reply_result.get("text", "")
        source = reply_result.get("source", "")

        if source == "stub":
            if "正在处理" in reply_text or "尽快为您" in reply_text or "已收到" in reply_text:
                return False

        if "无法" in reply_text or "抱歉" in reply_text or "不清楚" in reply_text:
            return False

        if "重复" in reply_text or "之前已" in reply_text:
            return False

        return True

    def _user_loop(
        self,
        context: ConversationContext,
        override_intent: Optional[str] = None,
        override_emotion: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not context.user_id or not context.order_id:
            users = self.user_simulator.list_user_orders(context.user_id or "", context.platform)
            if users:
                import random
                selected = random.choice(users)
                context.user_id = selected.get("user_id", context.user_id)
                context.order_id = selected.get("order_id", context.order_id)

        tool_results = []
        order_summary = self.user_simulator.get_order_summary(context.order_id, context.platform)
        if order_summary:
            context.add_tool_call("get_order_summary", {"order_id": context.order_id}, order_summary)
            tool_results.append(order_summary)

        shipment = self.user_simulator.get_shipment_summary(context.order_id, context.platform)
        if shipment:
            context.add_tool_call("get_shipment_summary", {"order_id": context.order_id}, shipment)
            tool_results.append(shipment)

        refund = self.user_simulator.get_refund_summary(context.order_id, context.platform)
        if refund:
            context.add_tool_call("get_refund_summary", {"order_id": context.order_id}, refund)
            tool_results.append(refund)

        emotion = override_emotion or context.emotion.value
        intent = override_intent or context.intent.value if context.intent else None

        result = self.user_simulator.generate(
            platform=context.platform,
            user_id=context.user_id,
            conversation_id=context.conversation_id,
        )

        user_message = result.user_message
        context.add_user_message(
            content=user_message,
            intent=result.decision.intent.value,
            emotion=result.decision.emotion.value,
        )

        context.emotion = EmotionType(result.decision.emotion.value)
        context.intent = IntentType(result.decision.intent.value)

        return {
            "user_message": user_message,
            "intent": result.decision.intent.value,
            "emotion": result.decision.emotion.value,
            "tool_calls": [
                {"name": tc.name, "arguments": tc.arguments}
                for tc in result.decision.tool_calls_used
            ],
            "tool_results": tool_results,
        }

    def _system_loop(
        self,
        context: ConversationContext,
        user_message: str,
    ) -> Dict[str, Any]:
        reply_context = {
            "platform": context.platform,
            "user_id": context.user_id,
            "order_id": context.order_id,
            "intent": context.intent.value if context.intent else "default",
            "emotion": context.emotion.value,
        }

        reply_result = self.reply_adapter.get_reply(
            run_id=context.run_id,
            user_message=user_message,
            context=reply_context,
        )

        context.add_reply_message(
            content=reply_result.get("text", ""),
            source=reply_result.get("source", "stub"),
        )

        return reply_result

    def run(
        self,
        platform: str,
        user_id: Optional[str] = None,
        order_id: Optional[str] = None,
        max_turns: int = 3,
        emotion: str = "calm",
        use_official_sim: bool = False,
    ) -> ConversationContext:
        context = self.create_run(
            platform=platform,
            user_id=user_id,
            order_id=order_id,
            max_turns=max_turns,
            emotion=emotion,
        )

        for _ in range(max_turns):
            if not context.should_continue():
                break

            turn_output = self.next_turn(context)
            print(f"Turn {turn_output.turn_no}: {turn_output.user_message[:30]}... -> {turn_output.reply_message[:30]}...")

        context.end(reason="completed")
        return context
