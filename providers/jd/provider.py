from typing import Dict, Any, Optional, List
import httpx
from providers.base.provider import BaseProvider, ProviderMode
from providers.utils.fixture_loader import FixtureLoader


class JdProvider(BaseProvider):
    def __init__(
        self,
        mode: ProviderMode = ProviderMode.MOCK,
        app_key: str = "test_app_key",
        app_secret: str = "test_app_secret",
        base_url: str = "https://api.jd.com",
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
        fixture = FixtureLoader.get_response("jd", "order_paid")
        data = fixture["jingdong_order_search_responce"]
        order_id_int = int(order_id.replace("JD_ORDER_", "").replace("JD", "0")) if not order_id.isdigit() else int(order_id)
        return {
            "order_id": order_id,
            "status": "wait_seller_delivery",
            "status_code": data["orderStatus"],
            "total_amount": str(data["orderTotalMoney"] / 100),
            "pay_amount": str(data["orderBuyerPayableMoney"] / 100),
            "freight": str(data["orderFreightMoney"] / 100),
            "receiver": {
                "name": data.get("buyerFullName"),
                "phone": data.get("buyerMobile"),
                "address": data.get("buyerFullAddress"),
            },
            "items": [
                {
                    "item_id": str(p.get("skuId", "")),
                    "name": p.get("skuName", ""),
                    "price": str(p.get("price", 0) / 100),
                    "quantity": p.get("num", 1),
                }
                for p in data.get("product", [])
            ],
            "create_time": data.get("orderStartTime"),
            "update_time": data.get("orderStatusTime"),
            "_raw_response": fixture,
        }

    async def _real_get_order(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/router/rest",
                params={
                    "method": "jd.order.get",
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
        fixture = FixtureLoader.get_response("jd", "order_paid")
        data = fixture["jingdong_order_search_responce"]
        orders = []
        for i in range(page_size):
            orders.append({
                "order_id": f"JD_ORDER_{page}_{i}",
                "status": "wait_seller_delivery",
                "total_amount": str(data["orderTotalMoney"] / 100),
            })
        return {
            "order_list": orders,
            "total_count": 100,
            "page": page,
            "page_size": page_size,
        }

    def get_shipment(self, order_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_shipment(order_id)
        return self._real_get_shipment(order_id)

    def _mock_get_shipment(self, order_id: str) -> Dict[str, Any]:
        fixture = FixtureLoader.get_response("jd", "order_shipped")
        data = fixture["jingdong_order_search_responce"]
        return {
            "order_id": order_id,
            "status": "in_transit",
            "status_code": data["orderStatus"],
            "company": data.get("deliveryCarrierName"),
            "tracking_no": data.get("deliveryBillNo"),
            "delivery_man": data.get("deliveryManName"),
            "delivery_phone": data.get("deliveryManPhone"),
            "package_weight": data.get("deliveryPackageWeight"),
            "confirm_time": data.get("deliveryConfirmTime"),
            "_raw_response": fixture,
        }

    def get_refund(self, refund_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_refund(refund_id)
        return self._real_get_refund(refund_id)

    def _mock_get_refund(self, refund_id: str) -> Dict[str, Any]:
        fixture = FixtureLoader.get_response("jd", "refund_applied")
        refund = fixture.get("refund", {})
        return {
            "refund_id": refund_id,
            "order_id": refund.get("order_id", "JD_ORDER_001"),
            "status": "approved",
            "refund_amount": str(refund.get("refund_amount", 0) / 100),
            "reason": refund.get("reason_desc", "商品不满意"),
            "apply_time": refund.get("apply_time"),
            "update_time": refund.get("update_time"),
            "_raw_response": fixture,
        }

    def create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_create_refund(order_id, reason, amount)
        return self._real_create_refund(order_id, reason, amount)

    def _mock_create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        fixture = FixtureLoader.get_response("jd", "refund_applied")
        refund = fixture.get("refund", {})
        return {
            "refund_id": f"JD_REF_{order_id}",
            "order_id": order_id,
            "status": refund.get("status", "applied"),
            "refund_amount": amount,
            "reason": reason,
            "apply_time": refund.get("apply_time"),
        }

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        raise NotImplementedError("JD does not support conversation API")

    def list_messages(self, conversation_id: str, limit: int = 100) -> Dict[str, Any]:
        raise NotImplementedError("JD does not support message API")