import httpx
from typing import Dict, Any, Optional
from .base import ReplyAdapter, ReplySource


class OfficialSimReplyAdapter(ReplyAdapter):
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def get_reply(
        self,
        run_id: str,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        platform = context.get("platform", "jd")
        order_id = context.get("order_id", "")
        user_id = context.get("user_id", "")
        intent = context.get("intent", "")

        try:
            response = self._call_official_sim(
                platform=platform,
                order_id=order_id,
                user_id=user_id,
                user_message=user_message,
                intent=intent,
            )
            return {
                "text": response.get("reply_text", ""),
                "source": ReplySource.OFFICIAL_SIM.value,
                "run_id": run_id,
                "platform": platform,
                "order_id": order_id,
                "api_response": response,
                "timestamp": self._get_timestamp(),
            }
        except Exception as e:
            return {
                "text": f"官方Sim调用失败: {str(e)}",
                "source": ReplySource.OFFICIAL_SIM.value,
                "run_id": run_id,
                "error": str(e),
                "fallback_to_stub": True,
                "timestamp": self._get_timestamp(),
            }

    def _call_official_sim(
        self,
        platform: str,
        order_id: str,
        user_id: str,
        user_message: str,
        intent: str,
    ) -> Dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/official-sim/runs",
                json={
                    "platform": platform,
                    "scenario_key": self._intent_to_scenario(intent),
                    "user_id": user_id,
                    "order_id": order_id,
                }
            )
            response.raise_for_status()
            return response.json()

    def _intent_to_scenario(self, intent: str) -> str:
        intent_to_scenario = {
            "ask_order_status": "order_wait_ship",
            "ask_shipment": "order_shipped",
            "ask_refund": "refund_pending",
            "refund_progress": "refund_processing",
            "complain": "complaint_handling",
            "product_question": "product_inquiry",
            "escalate_to_human": "transfer_to_human",
        }
        return intent_to_scenario.get(intent, "order_wait_ship")

    def get_source(self) -> ReplySource:
        return ReplySource.OFFICIAL_SIM

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
