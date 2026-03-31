import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Dict, Any, List, Optional, Literal, TypedDict
from enum import Enum
import random
import json

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from services.llm_service import LLMService
from providers.utils.fixture_loader import FixtureLoader
from nodes.evaluator import Evaluator, ValidationResult


class AgentStatus(str, Enum):
    IDLE = "idle"
    SELECTING_USER = "selecting_user"
    SELECTING_ORDER = "selecting_order"
    DECIDING_INTENT = "deciding_intent"
    CALLING_TOOLS = "calling_tools"
    RENDERING_MESSAGE = "rendering_message"
    VALIDATING_MESSAGE = "validating_message"
    EMITTING_MESSAGE = "emitting_message"
    COMPLETED = "completed"
    FAILED = "failed"


class UserSimulatorGraphState(TypedDict):
    platform: str
    user_id: Optional[str]
    order_id: Optional[str]
    conversation_id: Optional[str]

    status: str
    intent: Optional[str]
    emotion: Optional[str]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

    user_message: Optional[str]
    decision: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]

    errors: List[str]
    steps: List[Dict[str, Any]]


class UserSimulatorGraph:
    def __init__(self, model_name: Optional[str] = None):
        self.llm_service = LLMService(model_name=model_name)
        self.evaluator = Evaluator()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(UserSimulatorGraphState)

        workflow.add_node("select_user", self._select_user)
        workflow.add_node("select_order", self._select_order)
        workflow.add_node("decide_intent", self._decide_intent)
        workflow.add_node("call_tools", self._call_tools)
        workflow.add_node("render_message", self._render_message)
        workflow.add_node("validate_message", self._validate_message)
        workflow.add_node("emit_message", self._emit_message)

        workflow.set_entry_point("select_user")
        workflow.add_edge("select_user", "select_order")
        workflow.add_edge("select_order", "decide_intent")
        workflow.add_edge("decide_intent", "call_tools")
        workflow.add_edge("call_tools", "render_message")
        workflow.add_edge("render_message", "validate_message")
        workflow.add_edge("validate_message", "emit_message")
        workflow.add_edge("emit_message", END)

        return workflow.compile()

    def _select_user(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.SELECTING_USER.value

        if state.get("user_id"):
            state["steps"].append({
                "node": "select_user",
                "action": "use_provided_user",
                "user_id": state["user_id"],
            })
            return state

        users = FixtureLoader.list_users(state["platform"])
        if not users:
            state["errors"].append(f"No users found for platform: {state['platform']}")
            state["status"] = AgentStatus.FAILED.value
            return state

        selected = random.choice(users)
        state["user_id"] = selected
        state["steps"].append({
            "node": "select_user",
            "action": "random_select",
            "user_id": selected,
        })
        return state

    def _select_order(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.SELECTING_ORDER.value

        try:
            orders = FixtureLoader.get_user_orders(state["platform"], state["user_id"])
            if not orders:
                state["errors"].append(f"No orders found for user: {state['user_id']}")
                state["status"] = AgentStatus.FAILED.value
                return state

            selected = random.choice(orders)
            state["order_id"] = selected.get("order_id")
            state["steps"].append({
                "node": "select_order",
                "action": "random_select",
                "order_id": selected.get("order_id"),
            })
        except FileNotFoundError:
            state["errors"].append(f"User not found: {state['user_id']}")
            state["status"] = AgentStatus.FAILED.value

        return state

    def _decide_intent(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.DECIDING_INTENT.value

        order = None
        try:
            order = FixtureLoader.get_user_order(
                state["platform"],
                state["user_id"],
                state["order_id"]
            )
        except FileNotFoundError:
            order = None

        order_status = 'unknown'
        refund_status = 'none'
        shipment_status = 'none'

        if order:
            order_status = order.get('status', 'unknown')
            refund = order.get('refund')
            if refund:
                refund_status = refund.get('status', 'none')
            shipment = order.get('shipment')
            if shipment:
                shipment_status = shipment.get('status', 'none')

        intent_prompt = f"""根据订单状态，决定用户可能会有的意图。

订单ID: {state['order_id']}
订单状态: {order_status}
退款状态: {refund_status}
物流状态: {shipment_status}

请决定用户最可能的意图：
- ask_order_status: 询问订单状态
- ask_shipment: 询问物流
- ask_refund: 询问退款
- complain: 投诉
- escalate_to_human: 要求转人工
- product_question: 商品咨询

请输出JSON格式：
{{"intent": "意图", "emotion": "calm|impatient|angry", "reason": "决策原因"}}
"""

        messages = [{"role": "user", "content": intent_prompt}]
        response = self.llm_service.chat(messages)

        try:
            decision = json.loads(response)
            state["intent"] = decision.get("intent", "ask_order_status")
            state["emotion"] = decision.get("emotion", "calm")
            state["decision"] = decision
            state["steps"].append({
                "node": "decide_intent",
                "intent": state["intent"],
                "emotion": state["emotion"],
            })
        except json.JSONDecodeError:
            state["intent"] = "ask_order_status"
            state["emotion"] = "calm"
            state["decision"] = {"intent": "ask_order_status", "emotion": "calm", "reason": "parse_error"}
            state["steps"].append({
                "node": "decide_intent",
                "action": "parse_error_default",
            })

        return state

    def _call_tools(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.CALLING_TOOLS.value
        tool_results = []
        tool_calls = []

        order_id = state["order_id"]
        platform = state["platform"]

        order_result = FixtureLoader.get_user_order(platform, state["user_id"], order_id)
        if order_result:
            tool_results.append({"tool": "get_order_summary", "result": order_result})
            tool_calls.append({"name": "get_order_summary", "arguments": {"order_id": order_id, "platform": platform}})

        if order_result and order_result.get("shipment"):
            tool_results.append({"tool": "get_shipment_summary", "result": order_result["shipment"]})
            tool_calls.append({"name": "get_shipment_summary", "arguments": {"order_id": order_id, "platform": platform}})

        if order_result and order_result.get("refund"):
            tool_results.append({"tool": "get_refund_summary", "result": order_result["refund"]})
            tool_calls.append({"name": "get_refund_summary", "arguments": {"order_id": order_id, "platform": platform}})

        state["tool_results"] = tool_results
        state["tool_calls"] = tool_calls
        state["steps"].append({
            "node": "call_tools",
            "tools_called": [t["name"] for t in tool_calls],
        })

        return state

    def _render_message(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.RENDERING_MESSAGE.value

        system_prompt = """你是用户行为模拟器。你的任务是根据订单信息生成真实的用户消息。

## 核心约束
1. 你不能编造订单状态、物流状态、退款状态
2. 你只能依据提供的数据生成用户消息
3. 你扮演用户，不要替客服解释

## 用户消息要求
- 口语化，像真实用户
- 可以包含订单号等信息
- 不要太长，1-3句话
- 不要说客服视角的话

## 意图说明
- ask_order_status: 询问订单状态，如"我的订单到哪了"
- ask_shipment: 询问物流，如"快递什么时候到"
- ask_refund: 询问退款，如"退款什么时候到账"
- complain: 投诉，如"都几天了还不发货"
- escalate_to_human: 要求转人工
"""

        order_data = None
        for tr in state["tool_results"]:
            if tr.get("tool") == "get_order_summary":
                order_data = tr.get("result")
                break

        user_prompt = f"""订单信息: {json.dumps(order_data, ensure_ascii=False)}
物流信息: {json.dumps(state['tool_results'][1].get('result') if len(state['tool_results']) > 1 else {}, ensure_ascii=False)}
退款信息: {json.dumps(state['tool_results'][2].get('result') if len(state['tool_results']) > 2 else {}, ensure_ascii=False)}

请生成用户可能会说的话。"""

        messages = [{"role": "user", "content": user_prompt}]
        response = self.llm_service.chat(messages, system_prompt=system_prompt)

        state["user_message"] = response.strip()
        state["steps"].append({
            "node": "render_message",
            "message_length": len(state["user_message"]),
        })

        return state

    def _validate_message(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.VALIDATING_MESSAGE.value

        validation = self.evaluator.validate(
            message=state["user_message"],
            decision=state.get("decision", {}),
            tool_results=state["tool_results"],
            platform=state["platform"],
        )

        state["validation_result"] = {
            "passed": validation.passed,
            "errors": [{"field": e.field, "message": e.message} for e in validation.errors],
            "warnings": [{"field": w.field, "message": w.message} for w in validation.warnings],
        }

        state["steps"].append({
            "node": "validate_message",
            "passed": validation.passed,
            "error_count": validation.error_count,
        })

        if not validation.passed:
            state["errors"].extend([e.message for e in validation.errors])

        return state

    def _emit_message(self, state: UserSimulatorGraphState) -> UserSimulatorGraphState:
        state["status"] = AgentStatus.EMITTING_MESSAGE.value

        state["steps"].append({
            "node": "emit_message",
            "conversation_id": state.get("conversation_id"),
            "user_message": state["user_message"],
        })

        state["status"] = AgentStatus.COMPLETED.value
        return state

    def run(
        self,
        platform: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        initial_state: UserSimulatorGraphState = {
            "platform": platform,
            "user_id": user_id,
            "order_id": None,
            "conversation_id": conversation_id,
            "status": AgentStatus.IDLE.value,
            "intent": None,
            "emotion": None,
            "tool_calls": [],
            "tool_results": [],
            "user_message": None,
            "decision": None,
            "validation_result": None,
            "errors": [],
            "steps": [],
        }

        result = self.graph.invoke(initial_state)
        return result
