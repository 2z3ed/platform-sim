from typing import Dict, Any, List, Optional, Callable, Tuple
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from .llm_config import LLMConfig


class LLMService:
    def __init__(self, model_name: Optional[str] = None):
        self.config = LLMConfig()
        self.model_name = model_name or self._select_model()
        self.llm = self._create_llm()

    def _select_model(self) -> str:
        candidates = self.config.get_model_candidates()
        return candidates[0] if candidates else "qwen-plus"

    def _create_llm(self) -> ChatOpenAI:
        api_keys = self.config.get_api_keys()
        api_key = api_keys[0] if api_keys else os.getenv("DASHSCOPE_API_KEY", "")

        return ChatOpenAI(
            model=self.model_name,
            openai_api_key=api_key,
            openai_api_base=self.config.get_api_base(),
            temperature=0.7,
            max_tokens=500,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> str:
        langchain_messages = []

        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            langchain_messages.append(HumanMessage(content=content))

        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
            response = llm_with_tools.invoke(langchain_messages)
        else:
            response = self.llm.invoke(langchain_messages)

        return response.content if hasattr(response, "content") else str(response)

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """带工具调用的聊天，返回 (content, tool_calls)"""
        langchain_messages = []

        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            langchain_messages.append(HumanMessage(content=content))

        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
            response = llm_with_tools.invoke(langchain_messages)
        else:
            response = self.llm.invoke(langchain_messages)

        content = response.content if hasattr(response, "content") else str(response)
        
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "name": tc.get("name", ""),
                    "arguments": tc.get("args", {}),
                })

        return content, tool_calls

    def generate_suggestions(
        self,
        order_status: str,
        platform: str,
        user_message: str,
    ) -> List[str]:
        system_prompt = f"""你是一个电商客服助手。用户正在查询订单状态。

当前平台: {platform}
订单状态: {order_status}
用户消息: {user_message}

请生成3条合适的客服回复建议，每条建议不超过50字。"""

        messages = [{"role": "user", "content": user_message}]
        response = self.chat(messages, system_prompt=system_prompt)

        suggestions = [s.strip() for s in response.split("\n") if s.strip()]
        return suggestions[:3]

    def classify_intent(self, user_message: str) -> str:
        system_prompt = """你是一个客服意图分类器。用户消息可能是以下几种意图之一：
- refund_request (退款请求)
- shipment_inquiry (物流查询)
- order_cancellation (取消订单)
- general_inquiry (一般咨询)

请只输出一个意图分类标签，不要其他内容。"""

        messages = [{"role": "user", "content": user_message}]
        response = self.chat(messages, system_prompt=system_prompt)

        response = response.strip().lower()
        valid_intents = ["refund_request", "shipment_inquiry", "order_cancellation", "general_inquiry"]

        for intent in valid_intents:
            if intent in response:
                return intent

        return "general_inquiry"
