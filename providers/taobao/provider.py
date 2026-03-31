from typing import Dict, Any, Optional, List
import httpx
from providers.base.provider import BaseProvider, ProviderMode
from providers.utils.fixture_loader import FixtureLoader


class TaobaoProvider(BaseProvider):
    def __init__(
        self,
        mode: ProviderMode = ProviderMode.MOCK,
        app_key: str = "test_app_key",
        app_secret: str = "test_app_secret",
        base_url: str = "https://eco.taobao.com/router/rest",
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
        fixture = FixtureLoader.get_order_fixture("WAIT_SELLER_SEND_GOODS", "taobao")
        fixture["trade"]["tid"] = order_id
        for order in fixture.get("orders", {}).get("order", []):
            order["oid"] = f"{order_id}_{order['oid'][-1]}"
        return fixture

    async def _real_get_order(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "method": "taobao.trade.fullinfo.get",
                    "app_key": self.app_key,
                    "session": self.access_token,
                    "tid": order_id,
                    "fields": "tid,status,payment,total_fee,buyer_nick,receiver_name,receiver_mobile,receiver_state,receiver_city,receiver_district,receiver_address,orders",
                },
            )
            return response.json()

    def list_orders(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_list_orders(page, page_size)
        return self._real_list_orders(page, page_size)

    def _mock_list_orders(self, page: int, page_size: int) -> Dict[str, Any]:
        fixture = FixtureLoader.get_response("taobao", "trade_wait_ship")
        trades = []
        for i in range(page_size):
            trade = fixture["trade"].copy()
            trade["tid"] = f"TB_ORDER_{page}_{i}"
            trades.append(trade)
        return {
            "trades_sold_get_response": {
                "trades": {"trade": trades},
                "total_results": 100,
                "page_no": page,
                "page_size": page_size,
            }
        }

    def get_shipment(self, order_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_shipment(order_id)
        return self._real_get_shipment(order_id)

    def _mock_get_shipment(self, order_id: str) -> Dict[str, Any]:
        return {
            "sid": f"SID_{order_id}",
            "status": "shipped",
            "company_name": "顺丰速运",
            "out_sid": "SF1234567890",
            "send_time": "2026-03-29 14:00:00",
            "receiver_name": "张三",
            "receiver_mobile": "138****0000",
            "receiver_state": "浙江省",
            "receiver_city": "杭州市",
            "receiver_district": "余杭区",
            "receiver_address": "文一西路999号",
        }

    async def _real_get_shipment(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "method": "taobao.logistics.trace.search",
                    "app_key": self.app_key,
                    "session": self.access_token,
                    "tid": order_id,
                },
            )
            return response.json()

    def get_refund(self, refund_id: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_get_refund(refund_id)
        return self._real_get_refund(refund_id)

    def _mock_get_refund(self, refund_id: str) -> Dict[str, Any]:
        fixture = FixtureLoader.get_refund_fixture("refund_requested", "taobao")
        refund = fixture["refund"]
        refund["refund_id"] = refund_id
        return refund

    async def _real_get_refund(self, refund_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "method": "taobao.trade.refund.get",
                    "app_key": self.app_key,
                    "session": self.access_token,
                    "refund_id": refund_id,
                },
            )
            return response.json()

    def create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        if self.is_mock():
            return self._mock_create_refund(order_id, reason, amount)
        return self._real_create_refund(order_id, reason, amount)

    def _mock_create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        fixture = FixtureLoader.get_refund_fixture("refund_requested", "taobao")
        refund = fixture["refund"]
        refund["tid"] = order_id
        refund["refund_fee"] = amount
        refund["reason"] = reason
        refund["refund_id"] = f"REFUND_{order_id}"
        return refund

    async def _real_create_refund(self, order_id: str, reason: str, amount: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                params={
                    "method": "taobao.refund.create",
                    "app_key": self.app_key,
                    "session": self.access_token,
                    "tid": order_id,
                    "refund_fee": amount,
                    "reason": reason,
                },
            )
            return response.json()

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Taobao does not support conversation API")

    def list_messages(self, conversation_id: str, limit: int = 100) -> Dict[str, Any]:
        raise NotImplementedError("Taobao does not support message API")
