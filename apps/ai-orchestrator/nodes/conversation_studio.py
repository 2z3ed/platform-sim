from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from nodes.conversation import ConversationContext, EmotionType, IntentType
from nodes.conversation.context import Message
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


class AgentMessageTurnOutput(BaseModel):
    turn_no: int
    user_message: str
    intent: str
    emotion: str


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

        unhelpful_phrases = [
            "正在处理", "尽快为您", "已收到", "请耐心等待", "请您耐心等待",
            "无法", "抱歉", "不清楚", "重复", "之前已",
            "请问有什么可以帮您", "有什么可以帮",
        ]
        for phrase in unhelpful_phrases:
            if phrase in reply_text:
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

        conversation_history = [
            {"role": m.role, "content": m.content, "intent": m.intent, "emotion": m.emotion}
            for m in context.conversation_history
        ]
        turn_count = context.current_turn
        same_intent_count = context.get_repeated_count(intent or context.intent.value if context.intent else "")
        last_reply_resolved = context.consecutive_unsatisfied == 0

        order_status = order_summary.get("status", "") if order_summary else ""
        shipment_status = shipment.get("status", "") if shipment else ""
        refund_status = refund.get("status", "") if refund else ""
        product_name = ""
        if order_summary and order_summary.get("items"):
            items = order_summary["items"]
            if isinstance(items, list) and len(items) > 0:
                product_name = items[0] if isinstance(items[0], str) else items[0].get("name", "")
        last_logistics_node = ""
        if shipment and shipment.get("nodes"):
            nodes = shipment["nodes"]
            if isinstance(nodes, list) and len(nodes) > 0:
                last_node = nodes[-1]
                last_logistics_node = last_node.get("node", "") if isinstance(last_node, dict) else str(last_node)

        result = self.user_simulator.generate(
            platform=context.platform,
            user_id=context.user_id,
            conversation_id=context.conversation_id,
            override_emotion=override_emotion,
            override_intent=override_intent,
            conversation_history=conversation_history,
            turn_count=turn_count,
            same_intent_count=same_intent_count,
            last_reply_resolved=last_reply_resolved,
            order_summary=order_summary,
            shipment=shipment,
            refund=refund,
            order_status=order_status,
            shipment_status=shipment_status,
            refund_status=refund_status,
            product_name=product_name,
            last_logistics_node=last_logistics_node,
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

    def agent_message_turn(
        self,
        context: ConversationContext,
        agent_message: str,
    ) -> AgentMessageTurnOutput:
        context.current_turn += 1

        agent_msg = Message(
            role="agent",
            content=agent_message,
            timestamp=datetime.now().isoformat(),
        )
        context.conversation_history.append(agent_msg)

        conversation_history = [
            {"role": m.role, "content": m.content, "intent": m.intent, "emotion": m.emotion}
            for m in context.conversation_history
        ]
        turn_count = context.current_turn
        same_intent_count = context.get_repeated_count(context.intent.value if context.intent else "")

        if turn_count <= 1:
            reply_satisfactory = False
            last_reply_resolved = False
        else:
            reply_satisfactory = self._evaluate_reply_quality({"text": agent_message, "source": "agent"}, context.intent.value if context.intent else "")
            last_reply_resolved = reply_satisfactory

        order_summary = self.user_simulator.get_order_summary(context.order_id, context.platform)
        shipment = self.user_simulator.get_shipment_summary(context.order_id, context.platform)
        refund = self.user_simulator.get_refund_summary(context.order_id, context.platform)

        order_status = order_summary.get("status", "") if order_summary else ""
        shipment_status = shipment.get("status", "") if shipment else ""
        refund_status = refund.get("status", "") if refund else ""
        product_name = ""
        if order_summary and order_summary.get("items"):
            items = order_summary["items"]
            if isinstance(items, list) and len(items) > 0:
                product_name = items[0] if isinstance(items[0], str) else items[0].get("name", "")
        last_logistics_node = ""
        if shipment and shipment.get("nodes"):
            nodes = shipment["nodes"]
            if isinstance(nodes, list) and len(nodes) > 0:
                last_node = nodes[-1]
                last_logistics_node = last_node.get("node", "") if isinstance(last_node, dict) else str(last_node)

        result = self.user_simulator.generate(
            platform=context.platform,
            user_id=context.user_id,
            conversation_id=context.conversation_id,
            agent_message=agent_message,
            conversation_history=conversation_history,
            turn_count=turn_count,
            same_intent_count=same_intent_count,
            last_reply_resolved=last_reply_resolved,
            order_summary=order_summary,
            shipment=shipment,
            refund=refund,
            order_status=order_status,
            shipment_status=shipment_status,
            refund_status=refund_status,
            product_name=product_name,
            last_logistics_node=last_logistics_node,
        )

        user_message = result.user_message
        context.add_user_message(
            content=user_message,
            intent=result.decision.intent.value,
            emotion=result.decision.emotion.value,
        )

        context.emotion = EmotionType(result.decision.emotion.value)
        context.intent = IntentType(result.decision.intent.value)

        if not last_reply_resolved:
            context.consecutive_unsatisfied += 1
        else:
            context.consecutive_unsatisfied = 0

        return AgentMessageTurnOutput(
            turn_no=context.current_turn,
            user_message=user_message,
            intent=result.decision.intent.value,
            emotion=result.decision.emotion.value,
        )

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