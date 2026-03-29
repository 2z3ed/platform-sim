from typing import Dict, Any, List, Optional
from enum import Enum


class TaobaoOrderStatus(str, Enum):
    WAIT_PAY = "wait_pay"
    WAIT_SHIP = "wait_ship"
    SHIPPED = "shipped"
    TRADE_CLOSED = "trade_closed"
    FINISHED = "finished"


class TaobaoRefundStatus(str, Enum):
    NO_REFUND = "no_refund"
    REFUNDING = "refunding"
    REFUND_SUCCESS = "refund_success"
    REFUND_CLOSED = "refund_closed"


TAOBAO_ORDER_STATUS_TRANSITIONS: Dict[TaobaoOrderStatus, List[TaobaoOrderStatus]] = {
    TaobaoOrderStatus.WAIT_PAY: [TaobaoOrderStatus.WAIT_SHIP, TaobaoOrderStatus.TRADE_CLOSED],
    TaobaoOrderStatus.WAIT_SHIP: [TaobaoOrderStatus.SHIPPED, TaobaoOrderStatus.TRADE_CLOSED],
    TaobaoOrderStatus.SHIPPED: [TaobaoOrderStatus.FINISHED, TaobaoOrderStatus.TRADE_CLOSED],
    TaobaoOrderStatus.TRADE_CLOSED: [],
    TaobaoOrderStatus.FINISHED: [],
}


ORDER_SCENARIOS = {
    "wait_ship_basic": {
        "initial_order_status": TaobaoOrderStatus.WAIT_PAY,
        "steps": [
            {"action": "pay", "next_status": TaobaoOrderStatus.WAIT_SHIP},
        ],
    },
    "wait_ship_to_shipped": {
        "initial_order_status": TaobaoOrderStatus.WAIT_SHIP,
        "steps": [
            {"action": "ship", "next_status": TaobaoOrderStatus.SHIPPED},
        ],
    },
    "shipped_to_finished": {
        "initial_order_status": TaobaoOrderStatus.SHIPPED,
        "steps": [
            {"action": "confirm_receive", "next_status": TaobaoOrderStatus.FINISHED},
        ],
    },
    "full_flow": {
        "initial_order_status": TaobaoOrderStatus.WAIT_PAY,
        "steps": [
            {"action": "pay", "next_status": TaobaoOrderStatus.WAIT_SHIP},
            {"action": "ship", "next_status": TaobaoOrderStatus.SHIPPED},
            {"action": "confirm_receive", "next_status": TaobaoOrderStatus.FINISHED},
        ],
    },
}


def validate_status_transition(current: TaobaoOrderStatus, next_status: TaobaoOrderStatus) -> bool:
    allowed = TAOBAO_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: TaobaoOrderStatus) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "status": status.value,
        "total_amount": "99.99",
        "pay_amount": "99.99",
        "shipping_fee": "0.00",
        "receiver_name": "张三",
        "receiver_phone": "13800138000",
        "receiver_address": "浙江省杭州市余杭区",
        "created_at": "2026-03-01 10:00:00",
        "updated_at": "2026-03-29 12:00:00",
    }


def get_default_shipment_payload(order_id: str, status: str) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "status": status,
        "company": "顺丰速运",
        "tracking_no": "SF1234567890",
        "shipped_at": "2026-03-15 14:00:00",
        "delivered_at": None,
    }


def get_default_refund_payload(order_id: str, refund_id: str, status: TaobaoRefundStatus) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": status.value,
        "refund_amount": "50.00",
        "reason": "商品损坏",
        "created_at": "2026-03-20 10:00:00",
        "updated_at": "2026-03-29 12:00:00",
    }


def get_default_push_payload(event_type: str, order_id: str) -> Dict[str, Any]:
    push_templates = {
        "trade.OrderStatusChanged": {
            "event_type": "trade.OrderStatusChanged",
            "order_id": order_id,
            "old_status": "wait_pay",
            "new_status": "wait_ship",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "trade.ShipSent": {
            "event_type": "trade.ShipSent",
            "order_id": order_id,
            "logistics_company": "顺丰速运",
            "tracking_no": "SF1234567890",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "refund.RefundCreated": {
            "event_type": "refund.RefundCreated",
            "order_id": order_id,
            "refund_id": "REFUND001",
            "refund_amount": "50.00",
            "reason": "商品损坏",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
    }
    return push_templates.get(event_type, {"event_type": event_type, "order_id": order_id})
