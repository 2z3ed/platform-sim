import sys
from pathlib import Path
import re

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

SHIPMENT_IN_TRANSIT_STATUSES = {"shipped", "in_transit", "transit", "delivering", "运输中", "已发货", "派送中", "配送中"}
SHIPMENT_DELIVERED_STATUSES = {"delivered", "signed", "completed", "已签收", "已完成"}
SHIPMENT_RETURNED_STATUSES = {"returned", "退货已签收", "退货商品已签收"}
REFUND_IN_PROGRESS_STATUSES = {"pending_review", "reviewing", "processing", "refunding", "退款审核中", "退款处理中", "退款中", "审核中", "退款申请中"}
REFUND_COMPLETED_STATUSES = {"refunded", "completed", "closed", "退款完成", "退款成功", "退款关闭", "已退款", "已完成", "已关闭"}
ORDER_PENDING_SHIP_STATUSES = {"pending_shipment", "wait_ship", "待发货", "等待发货", "已付款", "paid"}

_NOT_PROVIDED = object()


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


class ResponseStrategy(str, Enum):
    FOLLOW_UP = "follow_up"
    CONFIRM = "confirm"
    EXPRESS_DISSATISFACTION = "express_dissatisfaction"
    DEMAND_COMPENSATION = "demand_compensation"
    PROVIDE_MORE_INFO = "provide_more_info"
    TEMPORARY_ACCEPT = "temporary_accept"
    SWITCH_TOPIC = "switch_topic"
    ESCALATE = "escalate"


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class UserMessageDecision(BaseModel):
    selected_user_id: str
    selected_order_id: Optional[str]
    intent: IntentType
    emotion: EmotionType
    strategy: ResponseStrategy
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


PLATFORM_STYLE_CONFIG = {
    "jd": {
        "name": "京东",
        "style": "direct",
        "traits": {
            "direct": True,
            "uses_honorifics": False,
            "mentions_tracking": True,
            "sentence_style": "short_direct",
            "tone": "result_oriented",
            "typical_phrases": ["快递到哪了", "物流信息", "京东物流", "单号多少"],
            "openers": ["", "查一下", "我问下"],
            "closers": ["", "给个准话", "说清楚点"],
            "escalation_style": "direct_demand",
            "followup_style": "direct_repeat",
        },
    },
    "taobao": {
        "name": "淘宝",
        "style": "colloquial",
        "traits": {
            "direct": False,
            "uses_honorifics": True,
            "mentions_tracking": True,
            "sentence_style": "negotiation",
            "tone": "casual_soft",
            "typical_phrases": ["麻烦帮我看下", "这边", "快递", "包邮"],
            "openers": ["麻烦帮我看下", "这边想问下", "帮我查下"],
            "closers": ["", "谢谢了", "麻烦了"],
            "escalation_style": "soft_complaint",
            "followup_style": "negotiation_repeat",
        },
    },
    "douyin_shop": {
        "name": "抖音小店",
        "style": "live_commerce",
        "traits": {
            "direct": True,
            "uses_honorifics": False,
            "mentions_tracking": True,
            "sentence_style": "live_context",
            "tone": "impulse_buy",
            "typical_phrases": ["直播间那个", "主播说的", "小黄车", "刚下单那个"],
            "openers": ["直播间那个", "主播推荐那个", "刚在直播间拍的"],
            "closers": ["", "主播可不是这么说的", "别是虚假宣传吧"],
            "escalation_style": "live_reference",
            "followup_style": "live_context_repeat",
        },
    },
    "wecom_kf": {
        "name": "企微客服",
        "style": "formal",
        "traits": {
            "direct": True,
            "uses_honorifics": True,
            "mentions_tracking": False,
            "sentence_style": "formal",
            "tone": "business",
            "typical_phrases": ["您好", "请问", "帮忙查一下"],
            "openers": ["您好", "请问", "打扰一下"],
            "closers": ["", "谢谢", "麻烦了"],
            "escalation_style": "formal_complaint",
            "followup_style": "formal_repeat",
        },
    },
    "xhs": {
        "name": "小红书",
        "style": "casual",
        "traits": {
            "direct": False,
            "uses_honorifics": False,
            "mentions_tracking": False,
            "sentence_style": "casual",
            "tone": "peer_recommend",
            "typical_phrases": ["姐妹们推荐的", "种草的", "那个商品"],
            "openers": ["", "就是那个", "我想问下"],
            "closers": ["", "姐妹们说这家不行", "别是踩雷了吧"],
            "escalation_style": "peer_reference",
            "followup_style": "casual_repeat",
        },
    },
    "kuaishou": {
        "name": "快手小店",
        "style": "live_commerce",
        "traits": {
            "direct": True,
            "uses_honorifics": False,
            "mentions_tracking": True,
            "sentence_style": "live_context",
            "tone": "impulse_buy",
            "typical_phrases": ["老铁推荐", "直播间", "下单那个"],
            "openers": ["直播间那个", "老铁推荐那个", "刚拍的"],
            "closers": ["", "别忽悠人", "说好的呢"],
            "escalation_style": "direct_demand",
            "followup_style": "direct_repeat",
        },
    },
}

CONTEXT_CITATION_PATTERNS = {
    "promise_time": [
        "你刚才说{claim}，现在呢",
        "上次不是说{claim}吗",
        "你前面让我{claim}，等到现在",
        "刚刚说{claim}，结果呢",
    ],
    "promise_action": [
        "你说{claim}，到现在没动静",
        "不是说要{claim}吗",
        "你让我{claim}，然后呢",
    ],
    "status_update": [
        "你刚说{claim}，具体什么情况",
        "你前面给的{claim}，我查了没找到",
    ],
}


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
        if ECD_TEMPLATES_PATH.exists():
            with open(ECD_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prompt_templates", {})
        return {}

    def _select_intent_from_order(self, order_summary: dict, shipment: dict, refund: dict) -> str:
        if refund and refund.get("status"):
            return "ask_refund"
        if shipment and shipment.get("status"):
            return "ask_shipment"
        return "ask_order_status"

    def _classify_business_stage(
        self,
        order_status: str,
        shipment_status: str,
        refund_status: str,
    ) -> str:
        rs = refund_status.strip().lower() if refund_status else ""
        ss = shipment_status.strip().lower() if shipment_status else ""
        os_ = order_status.strip().lower() if order_status else ""

        if any(k in rs for k in REFUND_IN_PROGRESS_STATUSES):
            return "refund_in_progress"
        if any(k in rs for k in REFUND_COMPLETED_STATUSES):
            return "refund_completed"
        if any(k in ss for k in SHIPMENT_DELIVERED_STATUSES):
            return "delivered"
        if any(k in ss for k in SHIPMENT_IN_TRANSIT_STATUSES):
            return "in_transit"
        if any(k in os_ for k in ORDER_PENDING_SHIP_STATUSES):
            return "pending_shipment"
        return "unknown"

    def _compute_forbidden_topics(self, stage: str) -> list:
        if stage == "refund_in_progress":
            return ["ask_order_status", "ask_shipment", "complain_shipment"]
        if stage == "refund_completed":
            return ["ask_order_status", "ask_shipment", "complain_shipment"]
        if stage == "delivered":
            return ["ask_order_status", "complain_shipment"]
        if stage == "in_transit":
            return ["ask_order_status"]
        if stage == "pending_shipment":
            return []
        return []

    def _compute_allowed_intents(self, stage: str) -> list:
        if stage == "refund_in_progress":
            return ["ask_refund", "complain", "escalate_to_human"]
        if stage == "refund_completed":
            return ["ask_refund", "product_question", "complain", "escalate_to_human"]
        if stage == "delivered":
            return ["product_question", "ask_refund", "complain", "escalate_to_human"]
        if stage == "in_transit":
            return ["ask_shipment", "complain", "escalate_to_human"]
        if stage == "pending_shipment":
            return ["ask_order_status", "ask_shipment", "complain", "escalate_to_human"]
        return ["ask_order_status", "ask_shipment", "ask_refund", "complain", "escalate_to_human"]

    def _ground_intent_to_state(
        self,
        candidate_intent: str,
        stage: str,
        allowed_intents: list,
        forbidden_topics: list,
    ) -> str:
        if candidate_intent in forbidden_topics:
            for intent in allowed_intents:
                if intent not in forbidden_topics:
                    return intent
            return allowed_intents[0] if allowed_intents else "ask_order_status"
        if candidate_intent in allowed_intents:
            return candidate_intent
        for intent in allowed_intents:
            if intent not in forbidden_topics:
                return intent
        return "ask_order_status"

    def _extract_context_claims(self, conversation_history: List[Dict[str, Any]]) -> Optional[str]:
        agent_msgs = [m.get("content", "") for m in conversation_history if m.get("role") == "agent"]
        if not agent_msgs:
            return None
        last_agent = agent_msgs[-1]
        if len(last_agent) > 60:
            last_agent = last_agent[:60]
        claim_patterns = [
            r"([0-9]+(?:小时|天|工作日|分钟)内(?:发货|处理|完成|到账|送达))",
            r"(今天(?:发货|处理|完成))",
            r"(明天(?:发货|处理|完成|到))",
            r"(已经(?:催|联系|通知|安排)(?:仓库|快递|物流|商家))",
            r"(单号(?:稍后|马上|尽快)(?:更新|发|给))",
            r"(预计(?:[0-9]+)?(?:天|小时|个工作日|小时内)?(?:送达|到达|处理完|发货))",
            r"(正在(?:安排|处理|审核|核实))",
            r"(尽快(?:为您|帮你|给您)?(?:处理|安排|核实|查询))",
            r"(预计.*?(?:[0-9]+)?(?:天|小时|工作日)?)",
        ]
        for pat in claim_patterns:
            m = re.search(pat, last_agent)
            if m:
                return m.group(1)
        if len(last_agent) > 10:
            short = last_agent[:20]
            return short
        return None

    def _build_utterance_plan(
        self,
        stage: str,
        intent: str,
        strategy: ResponseStrategy,
        same_intent_count: int,
        turn_count: int,
        agent_message: Optional[str],
        conversation_history: List[Dict[str, Any]],
        platform: str,
        product_name: str,
        last_logistics_node: str,
    ) -> Dict[str, Any]:
        plan = {
            "main_question": "",
            "tone_level": "normal",
            "cite_previous": False,
            "citation_text": "",
            "followup_type": "first_ask",
            "platform_style": "neutral",
        }

        claim = self._extract_context_claims(conversation_history)
        if claim and same_intent_count >= 1 and strategy in (ResponseStrategy.FOLLOW_UP, ResponseStrategy.EXPRESS_DISSATISFACTION):
            plan["cite_previous"] = True
            plan["citation_text"] = claim

        if same_intent_count == 0:
            plan["followup_type"] = "first_ask"
            plan["tone_level"] = "normal"
        elif same_intent_count == 1:
            plan["followup_type"] = "second_ask"
            plan["tone_level"] = "impatient"
        else:
            plan["followup_type"] = "third_plus"
            plan["tone_level"] = "angry"

        if strategy == ResponseStrategy.TEMPORARY_ACCEPT:
            plan["followup_type"] = "accept"
            plan["tone_level"] = "reluctant"
        elif strategy == ResponseStrategy.CONFIRM:
            plan["followup_type"] = "confirm"
            plan["tone_level"] = "normal"
        elif strategy == ResponseStrategy.DEMAND_COMPENSATION:
            plan["followup_type"] = "compensation"
            plan["tone_level"] = "demanding"
        elif strategy == ResponseStrategy.ESCALATE:
            plan["followup_type"] = "escalate"
            plan["tone_level"] = "angry"
        elif strategy == ResponseStrategy.EXPRESS_DISSATISFACTION:
            plan["followup_type"] = "complain"
            plan["tone_level"] = "angry"

        platform_config = PLATFORM_STYLE_CONFIG.get(platform, PLATFORM_STYLE_CONFIG["jd"])
        plan["platform_style"] = platform_config.get("style", "direct")

        if stage == "in_transit":
            if plan["followup_type"] == "first_ask":
                if last_logistics_node:
                    plan["main_question"] = f"物流一直停在{last_logistics_node}不动了，到底什么情况"
                else:
                    plan["main_question"] = "物流怎么不动了"
            elif plan["followup_type"] == "second_ask":
                if last_logistics_node:
                    if plan["cite_previous"] and plan["citation_text"]:
                        plan["main_question"] = f"你刚才说{plan['citation_text']}，物流还是停在{last_logistics_node}没动啊"
                    else:
                        plan["main_question"] = f"物流还是停在{last_logistics_node}，大概什么时候能恢复更新"
                else:
                    plan["main_question"] = "物流一直没更新，到底什么时候能恢复"
            elif plan["followup_type"] == "third_plus":
                if last_logistics_node:
                    if plan["cite_previous"] and plan["citation_text"]:
                        plan["main_question"] = f"你说{plan['citation_text']}，结果物流一直卡在{last_logistics_node}，这都几天了"
                    else:
                        plan["main_question"] = f"物流卡在{last_logistics_node}好几天了，你们到底怎么处理的"
                else:
                    plan["main_question"] = "物流好几天不动了，你们到底管不管"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = f"物流一直不动，{product_name}的事到底能不能解决"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "物流耽误这么久，你们打算怎么补偿"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "物流一直不更新，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我再等等物流更新"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的那我再看看物流"

        elif stage == "pending_shipment":
            if plan["followup_type"] == "first_ask":
                plan["main_question"] = f"{product_name}什么时候能发货" if product_name else "订单什么时候能发"
            elif plan["followup_type"] == "second_ask":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你刚才说{plan['citation_text']}，现在还没发呢"
                else:
                    plan["main_question"] = "到底什么时候能发货，给个准信"
            elif plan["followup_type"] == "third_plus":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你说{plan['citation_text']}，结果到现在没发，到底怎么回事"
                else:
                    plan["main_question"] = "一直不发货，你们到底能不能做"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = f"{product_name}一直不发货，到底能不能解决" if product_name else "一直不发货，到底能不能解决"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "发货拖这么久，你们打算怎么补偿"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "一直不发货，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我再等等发货"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的那我等发货通知"

        elif stage == "delivered":
            if plan["followup_type"] == "first_ask":
                if product_name:
                    plan["main_question"] = f"{product_name}收到有点问题"
                else:
                    plan["main_question"] = "收到的商品有点问题"
            elif plan["followup_type"] == "second_ask":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你刚才说{plan['citation_text']}，那具体怎么操作"
                else:
                    plan["main_question"] = "那售后流程到底是什么样的"
            elif plan["followup_type"] == "third_plus":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你说{plan['citation_text']}，到现在没人联系我"
                else:
                    plan["main_question"] = "售后一直没人处理，到底怎么回事"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = f"{product_name}质量有问题，你们到底管不管" if product_name else "商品有问题，到底管不管"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "收到的是坏的，你们打算怎么赔"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "售后一直不处理，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我按你说的操作看看"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的我知道了"

        elif stage == "refund_in_progress":
            if plan["followup_type"] == "first_ask":
                plan["main_question"] = "退款到哪一步了"
            elif plan["followup_type"] == "second_ask":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你刚才说{plan['citation_text']}，到现在还没动静"
                else:
                    plan["main_question"] = "退款到底还要等多久"
            elif plan["followup_type"] == "third_plus":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你说{plan['citation_text']}，结果到现在没到账，到底怎么回事"
                else:
                    plan["main_question"] = "退款一直不到账，你们到底在拖什么"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = "退款一直不处理，到底能不能解决"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "退款拖这么久，你们打算怎么补偿"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "退款一直不处理，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我再等等退款"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的那我等退款到账"

        elif stage == "refund_completed":
            if plan["followup_type"] == "first_ask":
                plan["main_question"] = "退款已经完成了吗"
            elif plan["followup_type"] == "second_ask":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你说{plan['citation_text']}，但我还没收到"
                else:
                    plan["main_question"] = "退款说完成了但我没看到钱"
            elif plan["followup_type"] == "third_plus":
                plan["main_question"] = "退款完成了好几天了我还没收到，到底退到哪了"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = "退款说完成了但钱没到，到底怎么回事"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "退款拖了这么久才完成，你们打算怎么补偿"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "退款问题一直没解决，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我再去银行查查看"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的那我查一下账户"

        else:
            if plan["followup_type"] == "first_ask":
                plan["main_question"] = f"{product_name}现在什么情况" if product_name else "订单到哪了"
            elif plan["followup_type"] == "second_ask":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你刚才说{plan['citation_text']}，然后呢"
                else:
                    plan["main_question"] = "那到底什么情况，给个准话"
            elif plan["followup_type"] == "third_plus":
                if plan["cite_previous"] and plan["citation_text"]:
                    plan["main_question"] = f"你说{plan['citation_text']}，结果还是没解决"
                else:
                    plan["main_question"] = "一直说在处理，到底什么时候能好"
            elif plan["followup_type"] == "complain":
                plan["main_question"] = f"{product_name}的事到底能不能解决" if product_name else "到底能不能解决"
            elif plan["followup_type"] == "compensation":
                plan["main_question"] = "耽误这么久，你们打算怎么补偿"
            elif plan["followup_type"] == "escalate":
                plan["main_question"] = "一直解决不了，转人工吧"
            elif plan["followup_type"] == "accept":
                plan["main_question"] = "行吧那我再等等"
            elif plan["followup_type"] == "confirm":
                plan["main_question"] = "好的我知道了"

        return plan

    def _apply_platform_style(
        self,
        message: str,
        plan: Dict[str, Any],
        platform: str,
        turn_count: int,
        intent: str,
    ) -> str:
        platform_config = PLATFORM_STYLE_CONFIG.get(platform, PLATFORM_STYLE_CONFIG["jd"])
        traits = platform_config.get("traits", {})
        style = traits.get("sentence_style", "direct")

        if style == "direct":
            message = message.strip()
            if turn_count == 0 and random.random() > 0.5:
                openers = traits.get("openers", [])
                opener = random.choice([o for o in openers if o]) if openers else ""
                if opener and random.random() > 0.5:
                    message = f"{opener}，{message}"
            if intent == "ask_shipment" and traits.get("mentions_tracking") and random.random() > 0.6:
                message = f"{message}，单号多少"
            closers = traits.get("closers", [])
            if random.random() > 0.7 and closers:
                closer = random.choice([c for c in closers if c])
                if closer:
                    message = f"{message}，{closer}"

        elif style == "negotiation":
            if turn_count == 0 and random.random() > 0.4:
                openers = traits.get("openers", [])
                opener = random.choice([o for o in openers if o]) if openers else ""
                if opener:
                    message = f"{opener}，{message}"
            if random.random() > 0.6:
                message = message.replace("到底", "").replace("到底", "")
            closers = traits.get("closers", [])
            if random.random() > 0.6 and closers:
                closer = random.choice([c for c in closers if c])
                if closer:
                    message = f"{message}，{closer}"

        elif style == "live_context":
            if turn_count == 0 and random.random() > 0.4:
                openers = traits.get("openers", [])
                opener = random.choice([o for o in openers if o]) if openers else ""
                if opener:
                    message = f"{opener}，{message}"
            closers = traits.get("closers", [])
            if random.random() > 0.6 and closers:
                closer = random.choice([c for c in closers if c])
                if closer:
                    message = f"{message}，{closer}"

        elif style == "formal":
            if turn_count == 0 and random.random() > 0.5:
                openers = traits.get("openers", [])
                opener = random.choice([o for o in openers if o]) if openers else ""
                if opener:
                    message = f"{opener}，{message}"
            closers = traits.get("closers", [])
            if random.random() > 0.5 and closers:
                closer = random.choice([c for c in closers if c])
                if closer:
                    message = f"{message}，{closer}"

        elif style == "casual":
            if turn_count == 0 and random.random() > 0.5:
                openers = traits.get("openers", [])
                opener = random.choice([o for o in openers if o]) if openers else ""
                if opener:
                    message = f"{opener}，{message}"
            closers = traits.get("closers", [])
            if random.random() > 0.6 and closers:
                closer = random.choice([c for c in closers if c])
                if closer:
                    message = f"{message}，{closer}"

        return message

    def _build_semantic_frame(
        self,
        order_status: str,
        shipment_status: str,
        refund_status: str,
        candidate_intent: str,
        emotion: str,
        strategy: ResponseStrategy,
        agent_message: Optional[str],
        conversation_history: List[Dict[str, Any]],
        turn_count: int,
    ) -> Dict[str, Any]:
        stage = self._classify_business_stage(order_status, shipment_status, refund_status)
        forbidden = self._compute_forbidden_topics(stage)
        allowed = self._compute_allowed_intents(stage)
        grounded_intent = self._ground_intent_to_state(candidate_intent, stage, allowed, forbidden)

        frame = {
            "business_stage": stage,
            "primary_intent": grounded_intent,
            "emotion": emotion,
            "strategy": strategy.value if isinstance(strategy, ResponseStrategy) else str(strategy),
            "forbidden_topics": forbidden,
            "allowed_topics": allowed,
            "order_status": order_status,
            "shipment_status": shipment_status,
            "refund_status": refund_status,
        }
        return frame

    def _determine_strategy(
        self,
        intent: str,
        emotion: str,
        agent_message: Optional[str],
        conversation_history: List[Dict[str, Any]],
        turn_count: int,
        same_intent_count: int,
        last_reply_resolved: bool,
    ) -> ResponseStrategy:
        user_msg_count = sum(1 for m in conversation_history if m.get("role") == "user")
        if user_msg_count == 0:
            if intent == "complain":
                return ResponseStrategy.EXPRESS_DISSATISFACTION
            if intent == "escalate_to_human":
                return ResponseStrategy.ESCALATE
            return ResponseStrategy.FOLLOW_UP

        if agent_message:
            if last_reply_resolved:
                if emotion == "angry":
                    return ResponseStrategy.TEMPORARY_ACCEPT
                return ResponseStrategy.CONFIRM
            if same_intent_count >= 2:
                if emotion == "angry":
                    return ResponseStrategy.ESCALATE
                return ResponseStrategy.DEMAND_COMPENSATION
            if "抱歉" in agent_message or "不好意思" in agent_message:
                if same_intent_count >= 1:
                    return ResponseStrategy.EXPRESS_DISSATISFACTION
                return ResponseStrategy.TEMPORARY_ACCEPT
            if "尽快" in agent_message or "正在处理" in agent_message or "稍等" in agent_message:
                if same_intent_count >= 2:
                    return ResponseStrategy.EXPRESS_DISSATISFACTION
                return ResponseStrategy.FOLLOW_UP
            if "无法" in agent_message or "不能" in agent_message:
                return ResponseStrategy.DEMAND_COMPENSATION
            if "单号" in agent_message or "物流" in agent_message or "快递" in agent_message:
                return ResponseStrategy.CONFIRM

        if same_intent_count >= 3:
            return ResponseStrategy.ESCALATE
        if same_intent_count >= 2:
            return ResponseStrategy.EXPRESS_DISSATISFACTION
        if intent == "escalate_to_human":
            return ResponseStrategy.ESCALATE
        if intent == "complain":
            return ResponseStrategy.EXPRESS_DISSATISFACTION

        return ResponseStrategy.FOLLOW_UP

    def _evolve_emotion(
        self,
        current_emotion: str,
        intent: str,
        agent_message: Optional[str],
        turn_count: int,
        same_intent_count: int,
        last_reply_resolved: bool,
    ) -> str:
        if turn_count == 0:
            if intent == "complain":
                return "impatient"
            if intent == "escalate_to_human":
                return "angry"
            return "calm"

        if last_reply_resolved:
            if current_emotion == "angry":
                return "impatient"
            if current_emotion == "impatient":
                return "calm"
            return current_emotion

        if agent_message:
            if "抱歉" in agent_message or "不好意思" in agent_message:
                if same_intent_count >= 2:
                    if current_emotion == "calm":
                        return "impatient"
                    return "angry"
                return current_emotion
            if "尽快" in agent_message or "正在处理" in agent_message or "稍等" in agent_message:
                if same_intent_count >= 2:
                    if current_emotion == "calm":
                        return "impatient"
                    return "angry"
                if current_emotion == "calm":
                    return "impatient"
                return current_emotion
            if "无法" in agent_message or "不能" in agent_message or "没办法" in agent_message:
                if current_emotion == "calm":
                    return "impatient"
                return "angry"

        if same_intent_count >= 3:
            return "angry"
        if same_intent_count >= 2:
            if current_emotion == "calm":
                return "impatient"
            return "angry"

        return current_emotion

    def _generate_message_with_context(
        self,
        intent: str,
        emotion: str,
        strategy: ResponseStrategy,
        platform: str,
        order_id: str,
        order_status: str,
        order_status_text: str,
        product_name: str,
        shipment_status: str,
        last_logistics_node: str,
        refund_status: str,
        agent_message: Optional[str],
        conversation_history: List[Dict[str, Any]],
        turn_count: int,
        same_intent_count: int,
        semantic_frame: Optional[Dict[str, Any]] = None,
    ) -> str:
        templates = self._load_ecd_templates()
        platform_config = PLATFORM_STYLE_CONFIG.get(platform, PLATFORM_STYLE_CONFIG["jd"])
        traits = platform_config.get("traits", {})

        stage = semantic_frame["business_stage"] if semantic_frame else "unknown"

        plan = self._build_utterance_plan(
            stage=stage,
            intent=intent,
            strategy=strategy,
            same_intent_count=same_intent_count,
            turn_count=turn_count,
            agent_message=agent_message,
            conversation_history=conversation_history or [],
            platform=platform,
            product_name=product_name,
            last_logistics_node=last_logistics_node,
        )

        message = plan["main_question"]

        message = self._apply_platform_style(
            message=message,
            plan=plan,
            platform=platform,
            turn_count=turn_count,
            intent=intent,
        )

        if plan["cite_previous"] and plan["citation_text"]:
            if "你刚才说" not in message and "你说" not in message and "上次" not in message:
                citation_patterns = CONTEXT_CITATION_PATTERNS.get("promise_time", [])
                citation = random.choice(citation_patterns).format(claim=plan["citation_text"])
                if random.random() > 0.5:
                    message = f"{citation}，{message}"

        if emotion == "impatient" and plan["tone_level"] != "angry" and strategy not in (ResponseStrategy.TEMPORARY_ACCEPT, ResponseStrategy.CONFIRM):
            impatient_modifiers = ["都好几天了", "怎么这么慢", "还要等多久"]
            if random.random() > 0.5:
                message = f"{message}，{random.choice(impatient_modifiers)}"
        elif emotion == "angry" and strategy not in (ResponseStrategy.TEMPORARY_ACCEPT, ResponseStrategy.CONFIRM, ResponseStrategy.ESCALATE):
            angry_modifiers = ["太离谱了", "什么破服务", "气死我了"]
            if random.random() > 0.5:
                message = f"{message}，{random.choice(angry_modifiers)}"

        if not message.endswith(("？", "?", "！", "!", "。", " ")) and random.random() > 0.3:
            message += "？"

        return message

    def _pick_state_constrained_template(
        self,
        intent: str,
        stage: str,
        templates: Dict[str, List[str]],
        product_name: str,
        order_id: str,
        shipment_status: str,
        last_logistics_node: str,
        refund_status: str,
    ) -> Optional[str]:
        if not templates or intent not in templates:
            return None

        base_candidates = list(templates[intent])

        if stage == "in_transit" and intent == "ask_shipment":
            base_candidates = [
                t for t in base_candidates
                if "怎么还没发货" not in t and "还没发货" not in t and "什么时候能发" not in t
            ]
            if not base_candidates and templates.get("ask_shipment"):
                base_candidates = [
                    t for t in templates["ask_shipment"]
                    if "怎么还没发货" not in t and "还没发货" not in t and "什么时候能发" not in t
                ]
            return random.choice(base_candidates) if base_candidates else "我的包裹到哪了"

        if stage == "delivered" and intent == "ask_shipment":
            base_candidates = [
                t for t in base_candidates
                if "怎么还没发货" not in t and "还没发货" not in t and "什么时候能发" not in t
            ]
            if base_candidates:
                return random.choice(base_candidates)
            return "物流显示已签收但我没收到"

        if stage == "refund_in_progress" and intent == "ask_refund":
            base_candidates = [
                t for t in base_candidates
                if "怎么还没发货" not in t and "还没发货" not in t
            ]
            if not base_candidates and templates.get("ask_refund"):
                base_candidates = templates["ask_refund"]
            return random.choice(base_candidates) if base_candidates else "退款审核到哪一步了"

        if stage == "pending_shipment" and intent == "ask_order_status":
            base_candidates = [
                t for t in base_candidates
                if "已签收" not in t and "物流显示" not in t
            ]
            if not base_candidates:
                base_candidates = templates.get("ask_order_status", ["订单什么时候能发"])
            return random.choice(base_candidates) if base_candidates else "什么时候能发货"

        if product_name and random.random() > 0.4:
            base_msg = random.choice(base_candidates) if base_candidates else templates[intent][0]
            if order_id and random.random() > 0.5:
                return f"{base_msg}，{product_name}，订单{order_id}"
            return f"{base_msg}，{product_name}"
        else:
            base_msg = random.choice(base_candidates) if base_candidates else templates[intent][0]
            if order_id and random.random() > 0.3:
                return f"{base_msg}，订单号{order_id}"
            return base_msg

    def _generate_message_from_template(self, intent: str, emotion: str, order_id: str) -> str:
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
        agent_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        turn_count: int = 0,
        same_intent_count: int = 0,
        last_reply_resolved: bool = False,
        order_summary=_NOT_PROVIDED,
        shipment=_NOT_PROVIDED,
        refund=_NOT_PROVIDED,
        order_status: str = "",
        shipment_status: str = "",
        refund_status: str = "",
        product_name: str = "",
        last_logistics_node: str = "",
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

        if order_summary is _NOT_PROVIDED:
            order_summary = self.get_order_summary(state.selected_order_id, platform)
        if shipment is _NOT_PROVIDED:
            shipment = self.get_shipment_summary(state.selected_order_id, platform)
        if refund is _NOT_PROVIDED:
            refund = self.get_refund_summary(state.selected_order_id, platform)

        if not product_name and order_summary and order_summary.get("items"):
            items = order_summary["items"]
            if isinstance(items, list) and len(items) > 0:
                product_name = items[0] if isinstance(items[0], str) else items[0].get("name", "")
        if not last_logistics_node and shipment and shipment.get("nodes"):
            nodes = shipment["nodes"]
            if isinstance(nodes, list) and len(nodes) > 0:
                last_node = nodes[-1]
                last_logistics_node = last_node.get("node", "") if isinstance(last_node, dict) else str(last_node)
        if not order_status and order_summary:
            order_status = order_summary.get("status", "")
        if not shipment_status and shipment:
            shipment_status = shipment.get("status", "")
        if not refund_status and refund:
            refund_status = refund.get("status", "")

        state.status = UserSimulatorStatus.GENERATING_MESSAGE

        if agent_message:
            if override_intent:
                candidate_intent = override_intent
            else:
                if "退款" in agent_message or "refund" in agent_message.lower():
                    candidate_intent = "ask_refund"
                elif "物流" in agent_message or "快递" in agent_message or "发货" in agent_message:
                    candidate_intent = "ask_shipment"
                elif "投诉" in agent_message or "人工" in agent_message:
                    candidate_intent = "escalate_to_human"
                else:
                    candidate_intent = "ask_order_status"

            emotion = self._evolve_emotion(
                current_emotion=override_emotion or "calm",
                intent=candidate_intent,
                agent_message=agent_message,
                turn_count=turn_count,
                same_intent_count=same_intent_count,
                last_reply_resolved=last_reply_resolved,
            )
        else:
            candidate_intent = override_intent if override_intent else self._select_intent_from_order(order_summary or {}, shipment or {}, refund or {})
            emotion = self._evolve_emotion(
                current_emotion=override_emotion or "calm",
                intent=candidate_intent,
                agent_message=None,
                turn_count=turn_count,
                same_intent_count=same_intent_count,
                last_reply_resolved=last_reply_resolved,
            )

        strategy = self._determine_strategy(
            intent=candidate_intent,
            emotion=emotion,
            agent_message=agent_message,
            conversation_history=conversation_history or [],
            turn_count=turn_count,
            same_intent_count=same_intent_count,
            last_reply_resolved=last_reply_resolved,
        )

        frame = self._build_semantic_frame(
            order_status=order_status,
            shipment_status=shipment_status,
            refund_status=refund_status,
            candidate_intent=candidate_intent,
            emotion=emotion,
            strategy=strategy,
            agent_message=agent_message,
            conversation_history=conversation_history or [],
            turn_count=turn_count,
        )

        grounded_intent = frame["primary_intent"]

        user_message = self._generate_message_with_context(
            intent=grounded_intent,
            emotion=emotion,
            strategy=strategy,
            platform=platform,
            order_id=state.selected_order_id or "",
            order_status=order_status,
            order_status_text=order_summary.get("status_text", "") if order_summary else "",
            product_name=product_name,
            shipment_status=shipment_status,
            last_logistics_node=last_logistics_node,
            refund_status=refund_status,
            agent_message=agent_message,
            conversation_history=conversation_history or [],
            turn_count=turn_count,
            same_intent_count=same_intent_count,
            semantic_frame=frame,
        )

        intent_enum = IntentType(grounded_intent) if grounded_intent in [i.value for i in IntentType] else IntentType.ASK_ORDER_STATUS
        emotion_enum = EmotionType(emotion) if emotion in [e.value for e in EmotionType] else EmotionType.CALM
        strategy_enum = ResponseStrategy(strategy) if strategy in [s.value for s in ResponseStrategy] else ResponseStrategy.FOLLOW_UP

        decision = UserMessageDecision(
            selected_user_id=state.selected_user_id,
            selected_order_id=state.selected_order_id,
            intent=intent_enum,
            emotion=emotion_enum,
            strategy=strategy_enum,
            tool_calls_used=[],
            reason=f"Context-aware generation, intent={grounded_intent}, emotion={emotion}, strategy={strategy}, stage={frame['business_stage']}, turn={turn_count}, same_intent={same_intent_count}, agent_message={'provided' if agent_message else 'none'}",
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
