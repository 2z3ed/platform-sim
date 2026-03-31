import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

FIXTURE_BASE_PATH = Path(__file__).parent.parent.parent / "apps" / "official-sim-server" / "fixtures"


class FixtureLoader:
    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def load(cls, platform: str, scenario_key: str, fixture_type: str = "success") -> Dict[str, Any]:
        cache_key = f"{platform}:{scenario_key}:{fixture_type}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        fixture_path = FIXTURE_BASE_PATH / platform / fixture_type / f"{scenario_key}.json"

        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")

        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture = json.load(f)

        cls._cache[cache_key] = fixture
        return fixture

    @classmethod
    def get_response(cls, platform: str, scenario_key: str, fixture_type: str = "success") -> Dict[str, Any]:
        fixture = cls.load(platform, scenario_key, fixture_type)
        return fixture.get("response", {})

    @classmethod
    def get_order_fixture(cls, status: str, platform: str = "taobao") -> Dict[str, Any]:
        mapping = {
            "WAIT_BUYER_PAY": "trade_wait_pay",
            "WAIT_SELLER_SEND_GOODS": "trade_wait_ship",
            "WAIT_BUYER_CONFIRM_GOODS": "trade_shipped",
            "TRADE_FINISHED": "trade_finished",
            "wait_pay": "trade_wait_pay",
            "wait_ship": "trade_wait_ship",
            "shipped": "trade_shipped",
            "finished": "trade_finished",
        }
        scenario_key = mapping.get(status, "trade_wait_ship")
        return cls.get_response(platform, scenario_key)

    @classmethod
    def get_refund_fixture(cls, status: str, platform: str = "taobao") -> Dict[str, Any]:
        mapping = {
            "REFUND_REQUEST": "refund_requested",
            "WAIT_SELLER_AGREE": "refund_requested",
            "refunding": "refund_requested",
            "refund_requested": "refund_requested",
        }
        scenario_key = mapping.get(status, "refund_requested")
        return cls.get_response(platform, scenario_key)

    @classmethod
    def get_order(cls, platform: str, order_id: str) -> Optional[Dict[str, Any]]:
        user_data = cls.get_user_by_order(platform, order_id)
        if user_data:
            for order in user_data.get("orders", []):
                if order.get("order_id") == order_id:
                    return order.get("official_response", order)
        return None

    @classmethod
    def get_shipment(cls, platform: str, order_id: str) -> Optional[Dict[str, Any]]:
        user_data = cls.get_user_by_order(platform, order_id)
        if user_data:
            for order in user_data.get("orders", []):
                if order.get("order_id") == order_id:
                    shipment = order.get("shipment", {})
                    if shipment:
                        return shipment.get("official_response", shipment)
        return None

    @classmethod
    def get_refund(cls, platform: str, order_id: str) -> Optional[Dict[str, Any]]:
        user_data = cls.get_user_by_order(platform, order_id)
        if user_data:
            for order in user_data.get("orders", []):
                if order.get("order_id") == order_id:
                    refund = order.get("refund", {})
                    if refund:
                        return refund.get("official_response", refund)
        return None

    @classmethod
    def list_fixtures(cls, platform: str, fixture_type: str = "success") -> list:
        fixture_dir = FIXTURE_BASE_PATH / platform / fixture_type
        if not fixture_dir.exists():
            return []
        return [f.stem for f in fixture_dir.glob("*.json")]

    @classmethod
    def list_users(cls, platform: str) -> list:
        user_dir = FIXTURE_BASE_PATH / platform / "users"
        if not user_dir.exists():
            return []
        return [f.stem for f in user_dir.glob("*.json")]

    @classmethod
    def load_user(cls, platform: str, user_id: str) -> Dict[str, Any]:
        cache_key = f"user:{platform}:{user_id}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        user_path = FIXTURE_BASE_PATH / platform / "users" / f"{user_id}.json"
        if not user_path.exists():
            raise FileNotFoundError(f"User fixture not found: {user_path}")

        with open(user_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        cls._cache[cache_key] = user_data
        return user_data

    @classmethod
    def get_user_order(cls, platform: str, user_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        user_data = cls.load_user(platform, user_id)
        for order in user_data.get("orders", []):
            if order.get("order_id") == order_id:
                return order
        return None

    @classmethod
    def get_user_orders(cls, platform: str, user_id: str) -> list:
        user_data = cls.load_user(platform, user_id)
        return user_data.get("orders", [])

    @classmethod
    def get_user_by_order(cls, platform: str, order_id: str) -> Optional[Dict[str, Any]]:
        for user_id in cls.list_users(platform):
            user_data = cls.load_user(platform, user_id)
            for order in user_data.get("orders", []):
                if order.get("order_id") == order_id:
                    return user_data
        return None

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
