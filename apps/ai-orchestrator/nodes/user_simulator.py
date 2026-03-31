import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
import json
import random

from services.llm_service import LLMService
from providers.utils.fixture_loader import FixtureLoader

ECD_TEMPLATES_PATH = Path(__file__).parent.parent / "data" / "extracted_user_queries" / "user_prompt_templates.json"


class UserSimulatorStatus(str, Enum):
    IDLE = "idle"
    SELECTING_USER = "selecting_user"
    QUERYING_DATA = "querying_data"
    GENERATING_MESSAGE = "generating_message"
    COMPLETED = "completed"
    FAILED = "failed"


class IntentType(str, Enum):
    ASK_ORDER_STATUS = "ask_order_status"
    ASK_SHIPMENT = "ask_shipment"
    ASK_REFUND = "ask_refund"
    COMPLAIN = "complain"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    PRODUCT_QUESTION = "product_question"


class EmotionType(str, Enum):
    CALM = "calm"
    IMPATIENT = "impatient"
    ANGRY = "angry"


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class UserMessageDecision(BaseModel):
    selected_user_id: str
    selected_order_id: Optional[str]
    intent: IntentType
    emotion: EmotionType
    tool_calls_used: List[ToolCall]
    reason: str


class UserSimulatorOutput(BaseModel):
    decision: UserMessageDecision
    user_message: str


class UserSimulatorState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: UserSimulatorStatus = UserSimulatorStatus.IDLE
    platform: Optional[str] = None
    selected_user_id: Optional[str] = None
    selected_order_id: Optional[str] = None
    intent: Optional[IntentType] = None
    emotion: Optional[EmotionType] = None
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    user_message: Optional[str] = None
    decision: Optional[UserMessageDecision] = None
    errors: List[str] = Field(default_factory=list)


class UserSimulator:
    def __init__(self, model_name: Optional[str] = None):
        self.llm_service = LLMService(model_name=model_name)

    def list_user_orders(self, user_id: str, platform: str) -> List[Dict[str, Any]]:
        try:
            orders = FixtureLoader.get_user_orders(platform, user_id)
            return orders
        except FileNotFoundError:
            return []

    def get_order_summary(self, order_id: str, platform: str) -> Optional[Dict[str, Any]]:
        order = FixtureLoader.get_user_by_order(platform, order_id)
        if order:
            for o in order.get("orders", []):
                if o.get("order_id") == order_id:
                    return {
                        "order_id": o.get("order_id"),
                        "status": o.get("status"),
                        "status_text": o.get("status_text"),
                        "amount": o.get("amount"),
                        "items": [item.get("name") for item in o.get("items", [])],
                    }
        return None

    def get_shipment_summary(self, order_id: str, platform: str) -> Optional[Dict[str, Any]]:
        for uid in FixtureLoader.list_users(platform):
            try:
                order = FixtureLoader.get_user_order(platform, uid, order_id)
                if order:
                    shipment = order.get("shipment")
                    if shipment:
                        return shipment
            except FileNotFoundError:
                continue
        return None

    def get_refund_summary(self, order_id: str, platform: str) -> Optional[Dict[str, Any]]:
        for uid in FixtureLoader.list_users(platform):
            try:
                order = FixtureLoader.get_user_order(platform, uid, order_id)
                if order:
                    refund = order.get("refund")
                    if refund:
                        return refund
            except FileNotFoundError:
                continue
        return None

    def emit_user_message(
        self,
        conversation_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "message": message,
            "metadata": metadata or {},
            "success": True,
        }

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_user_orders",
                "description": "获取用户所有订单列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户ID"},
                        "platform": {"type": "string", "description": "平台名称"},
                    },
                    "required": ["user_id", "platform"],
                },
            },
            {
                "name": "get_order_summary",
                "description": "获取订单摘要(用户视角)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "订单ID"},
                        "platform": {"type": "string", "description": "平台名称"},
                    },
                    "required": ["order_id", "platform"],
                },
            },
            {
                "name": "get_shipment_summary",
                "description": "获取物流摘要",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "订单ID"},
                        "platform": {"type": "string", "description": "平台名称"},
                    },
                    "required": ["order_id", "platform"],
                },
            },
            {
                "name": "get_refund_summary",
                "description": "获取退款摘要",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "订单ID"},
                        "platform": {"type": "string", "description": "平台名称"},
                    },
                    "required": ["order_id", "platform"],
                },
            },
        ]

    def _load_ecd_templates(self) -> Dict[str, List[str]]:
        """加载ECD用户消息模板"""
        if ECD_TEMPLATES_PATH.exists():
            with open(ECD_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prompt_templates", {})
        return {}

    def _select_intent_from_order(self, order_summary: dict, shipment: dict, refund: dict) -> str:
        """根据订单状态选择意图"""
        if refund and refund.get("status"):
            return "ask_refund"
        if shipment and shipment.get("status"):
            return "ask_shipment"
        return "ask_order_status"

    def _generate_message_from_template(self, intent: str, emotion: str, order_id: str) -> str:
        """从模板生成用户消息"""
        templates = self._load_ecd_templates()
        
        if templates and intent in templates:
            base_msg = random.choice(templates[intent])
            
            emotion_modifiers = {
                "impatient": ["都好几天了", "怎么这么慢", "还要等多久"],
                "angry": ["太离谱了", "什么破服务", "我要投诉"]
            }
            
            if emotion in emotion_modifiers and random.random() > 0.5:
                modifier = random.choice(emotion_modifiers[emotion])
                if order_id and random.random() > 0.5:
                    return f"{base_msg}，订单号{order_id}，{modifier}"
                return f"{base_msg}，{modifier}"
            
            if order_id and random.random() > 0.3:
                return f"{base_msg}，订单号{order_id}"
            
            return base_msg
        
        return f"我的订单{order_id}怎么样了"

    def build_system_prompt(self, platform: str) -> str:
        templates = self._load_ecd_templates()

        templates_section = ""
        if templates:
            templates_section = "\n\n## 真实用户消息模板参考（来自电商客服数据）\n"
            for intent, tmpls in templates.items():
                templates_section += f"\n### {intent}:\n"
                for t in tmpls[:5]:
                    templates_section += f"- \"{t}\"\n"

        return f"""你是用户模拟器，生成真实用户会说的话。

## 绝对禁止（违反直接失败）
- 禁止出现"亲"字 - 这是客服用语
- 禁止"请问"、"麻烦"、"您好" - 太客气
- 禁止"~"符号 - 不自然
- 禁止"确认一下" - 用户不这么说

## 用户说话风格
直接、口语、简短、有目的性

## 正确示例
- 订单TB001到哪了
- 退款怎么还没到账
- 发货了吗
- 快递单号多少
- 怎么还没发货

## 输出格式
{{
  "decision": {{
    "intent": "ask_order_status|ask_shipment|ask_refund|complain|escalate_to_human",
    "emotion": "calm|impatient|angry"
  }},
  "user_message": "用户说的话"
}}"""

    def generate(
        self,
        platform: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        override_emotion: Optional[str] = None,
        override_intent: Optional[str] = None,
    ) -> UserSimulatorOutput:
        state = UserSimulatorState(platform=platform)

        if user_id:
            state.selected_user_id = user_id
        else:
            users = FixtureLoader.list_users(platform)
            if not users:
                raise ValueError(f"No users found for platform: {platform}")
            state.selected_user_id = random.choice(users)

        state.status = UserSimulatorStatus.QUERYING_DATA

        orders = self.list_user_orders(state.selected_user_id, platform)
        if not orders:
            raise ValueError(f"No orders found for user: {state.selected_user_id}")

        selected_order = random.choice(orders)
        state.selected_order_id = selected_order.get("order_id")

        system_prompt = """你是用户模拟器。你需要：
1. 先调用工具获取订单信息
2. 根据订单状态决定用户意图
3. 从模板选择合适的用户消息

## 可用工具
- get_order_summary: 获取订单详情
- get_shipment_summary: 获取物流信息  
- get_refund_summary: 获取退款信息

## 意图类型
- ask_order_status: 询问订单状态
- ask_shipment: 询问物流
- ask_refund: 询问退款
- complain: 投诉
- escalate_to_human: 转人工

请先调用工具获取订单信息。"""

        user_prompt = f"""平台: {platform}
用户ID: {state.selected_user_id}
订单ID: {state.selected_order_id}

请调用工具获取订单信息，然后决定用户意图。"""

        try:
            content, tool_calls = self.llm_service.chat_with_tools(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                tools=self.get_available_tools()
            )
            
            state.tool_results = []
            for tc in tool_calls:
                args = tc.get("arguments", {})
                order_id = args.get("order_id", state.selected_order_id)
                
                if tc["name"] == "get_order_summary":
                    result = self.get_order_summary(order_id, platform)
                    state.tool_results.append({"tool": tc["name"], "result": result})
                elif tc["name"] == "get_shipment_summary":
                    result = self.get_shipment_summary(order_id, platform)
                    if result:
                        state.tool_results.append({"tool": tc["name"], "result": result})
                elif tc["name"] == "get_refund_summary":
                    result = self.get_refund_summary(order_id, platform)
                    if result:
                        state.tool_results.append({"tool": tc["name"], "result": result})
            
            order_summary = state.tool_results[0]["result"] if state.tool_results else {}
            shipment = state.tool_results[1]["result"] if len(state.tool_results) > 1 else {}
            refund = state.tool_results[2]["result"] if len(state.tool_results) > 2 else {}
            
        except Exception as e:
            order_summary = self.get_order_summary(state.selected_order_id, platform)
            shipment = self.get_shipment_summary(state.selected_order_id, platform)
            refund = self.get_refund_summary(state.selected_order_id, platform)
            tool_calls = [{"name": "get_order_summary", "arguments": {"order_id": state.selected_order_id, "platform": platform}}]

        state.status = UserSimulatorStatus.GENERATING_MESSAGE

        intent = override_intent if override_intent else self._select_intent_from_order(order_summary, shipment, refund)
        emotion = override_emotion if override_emotion else random.choice(["calm", "impatient", "angry"])
        
        user_message = self._generate_message_from_template(intent, emotion, state.selected_order_id)
        
        intent_enum = IntentType(intent) if intent in [i.value for i in IntentType] else IntentType.ASK_ORDER_STATUS
        emotion_enum = EmotionType(emotion) if emotion in [e.value for e in EmotionType] else EmotionType.CALM

        decision = UserMessageDecision(
            selected_user_id=state.selected_user_id,
            selected_order_id=state.selected_order_id,
            intent=intent_enum,
            emotion=emotion_enum,
            tool_calls_used=[ToolCall(name=tc["name"], arguments=tc.get("arguments", {})) for tc in tool_calls],
            reason=f"LLM tool calls + template, intent={intent}, emotion={emotion}",
        )

        state.decision = decision
        state.user_message = user_message
        state.status = UserSimulatorStatus.COMPLETED

        return UserSimulatorOutput(decision=decision, user_message=user_message)

    def _fallback_generate(self, state, order_summary, shipment, refund) -> str:
        import json
        
        order_status = order_summary.get("status", "unknown") if order_summary else "unknown"
        order_id = state.selected_order_id
        
        templates = {
            "ask_order_status": [
                f"我的订单{order_id}到哪了？",
                f"订单{order_id}现在什么状态？",
                f"帮我查一下订单{order_id}",
            ],
            "ask_shipment": [
                f"快递到哪了？单号是多少？",
                f"我的包裹什么时候能到？",
                f"物流信息帮我查一下",
            ],
            "ask_refund": [
                f"我的退款什么时候到账？",
                f"退款进度怎么样了？",
                f"申请退款多久能处理？",
            ],
        }
        
        if shipment and shipment.get("status"):
            intent = "ask_shipment"
        elif refund and refund.get("status"):
            intent = "ask_refund"
        else:
            intent = "ask_order_status"
        
        user_messages = templates.get(intent, templates["ask_order_status"])
        user_message = random.choice(user_messages)
        
        return json.dumps({
            "decision": {
                "selected_user_id": state.selected_user_id,
                "selected_order_id": order_id,
                "intent": intent,
                "emotion": "calm",
                "tool_calls_used": [{"name": "get_order_summary", "arguments": {"order_id": order_id}}],
                "reason": "Fallback mode - LLM unavailable"
            },
            "user_message": user_message
        }, ensure_ascii=False)
