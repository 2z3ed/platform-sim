from typing import Dict, Any, Optional, List
import httpx
from providers.base.provider import BaseProvider, ProviderMode


class XhsProvider(BaseProvider):
    def __init__(
        self,
        mode: ProviderMode = ProviderMode.MOCK,
        app_key: str = "test_app_key",
        app_secret: str = "test_app_secret",
        base_url: str = "https://open.xiaohongshu.com",
    ):
        super().__init__(mode)
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.access_token: Optional[str] = None

    def get_order(self, order_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_order(order_id)
        return self._real_get_order(order_id)

    def _mock_get_order(self, order_id: str) -> Dict[str, Any]:
        return {
            "order_id": order_id,
            "status": "delivering",
            "total_amount": "149.99",
            "pay_amount": "149.99",
            "freight": "0.00",
            "receiver": {
                "name": "赵六",
                "phone": "136****6000",
                "address": "广东省广州市天河区",
            },
            "customs": {
                "status": "declared",
                "id_card": "440***************1234",
            },
            "items": [
                {
                    "item_id": "XHS_ITEM_001",
                    "name": "小红书特卖商品",
                    "price": "149.99",
                    "quantity": 1,
                }
            ],
            "create_time": "2026-03-01 10:00:00",
            "update_time": "2026-03-29 12:00:00",
        }

    async def _real_get_order(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/order/detail",
                params={
                    "app_key": self.app_key,
                    "access_token": self.access_token,
                    "order_id": order_id,
                },
            )
            return response.json()

    def list_orders(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_list_orders(page, page_size)
        return self._real_list_orders(page, page_size)

    def _mock_list_orders(self, page: int, page_size: int) -> Dict[str, Any]:
        return {
            "order_list": [
                {
                    "order_id": f"XHS_ORDER_{page}_{i}",
                    "status": "delivering",
                    "total_amount": "149.99",
                }
                for i in range(page_size)
            ],
            "total_count": 100,
            "page": page,
            "page_size": page_size,
        }

    def get_shipment(self, order_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_shipment(order_id)
        return self._real_get_shipment(order_id)

    def _mock_get_shipment(self, order_id: str) -> Dict[str, Any]:
        return {
            "order_id": order_id,
            "shipment_id": f"XHS_SHIP_{order_id}",
            "status": "in_transit",
            "company": "顺丰速运",
            "tracking_no": "SF1234567890",
            "nodes": [
                {
                    "node": "已揽收",
                    "time": "2026-03-15 14:00:00",
                    "description": "快件已被揽收",
                },
                {
                    "node": "运输中",
                    "time": "2026-03-16 08:00:00",
                    "description": "快件正在运输途中",
                },
            ],
        }

    def get_refund(self, refund_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_refund(refund_id)
        return self._real_get_refund(refund_id)

    def _mock_get_refund(self, refund_id: str) -> Dict[str, Any]:
        return {
            "refund_id": refund_id,
            "order_id": "XHS_ORDER_001",
            "status": "processing",
            "refund_amount": "149.99",
            "reason": "商品损坏",
            "apply_time": "2026-03-20 10:00:00",
            "update_time": "2026-03-29 12:00:00",
        }

    def create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_create_refund(order_id, reason, amount)
        return self._real_create_refund(order_id, reason, amount)

    def _mock_create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        return {
            "refund_id": f"XHS_REF_{order_id}",
            "order_id": order_id,
            "status": "applied",
            "refund_amount": amount,
            "reason": reason,
            "apply_time": "2026-03-29 12:00:00",
        }

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        raise NotImplementedError("XHS does not support conversation API")

    def list_messages(self, conversation_id: str, limit: int = 100) -> Dict[str, Any]:
        raise NotImplementedError("XHS does not support message API")
