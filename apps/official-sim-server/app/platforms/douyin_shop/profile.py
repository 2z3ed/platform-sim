from typing import Dict, Any, List, Optional
from enum import Enum


class DouyinOrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDING = "refunding"
    REFUNDED = "refunded"


class DouyinRefundStatus(str, Enum):
    NO_REFUND = "no_refund"
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDING = "refunding"
    REFUNDED = "refunded"
    CLOSED = "closed"


DOUYIN_ORDER_STATUS_TRANSITIONS: Dict[DouyinOrderStatus, List[DouyinOrderStatus]] = {
    DouyinOrderStatus.CREATED: [DouyinOrderStatus.PAID, DouyinOrderStatus.CANCELLED],
    DouyinOrderStatus.PAID: [DouyinOrderStatus.SHIPPED, DouyinOrderStatus.REFUNDING],
    DouyinOrderStatus.SHIPPED: [DouyinOrderStatus.CONFIRMED, DouyinOrderStatus.REFUNDING],
    DouyinOrderStatus.CONFIRMED: [DouyinOrderStatus.COMPLETED, DouyinOrderStatus.REFUNDING],
    DouyinOrderStatus.COMPLETED: [DouyinOrderStatus.REFUNDING],
    DouyinOrderStatus.CANCELLED: [],
    DouyinOrderStatus.REFUNDING: [DouyinOrderStatus.REFUNDED, DouyinOrderStatus.CANCELLED],
    DouyinOrderStatus.REFUNDED: [],
}


ORDER_SCENARIOS = {
    "basic_paid_to_shipped": {
        "initial_order_status": DouyinOrderStatus.PAID,
        "steps": [
            {"action": "ship", "next_status": DouyinOrderStatus.SHIPPED},
        ],
    },
    "basic_shipped_to_confirmed": {
        "initial_order_status": DouyinOrderStatus.SHIPPED,
        "steps": [
            {"action": "confirm", "next_status": DouyinOrderStatus.CONFIRMED},
        ],
    },
    "basic_confirmed_to_completed": {
        "initial_order_status": DouyinOrderStatus.CONFIRMED,
        "steps": [
            {"action": "complete", "next_status": DouyinOrderStatus.COMPLETED},
        ],
    },
    "full_flow": {
        "initial_order_status": DouyinOrderStatus.CREATED,
        "steps": [
            {"action": "pay", "next_status": DouyinOrderStatus.PAID},
            {"action": "ship", "next_status": DouyinOrderStatus.SHIPPED},
            {"action": "confirm", "next_status": DouyinOrderStatus.CONFIRMED},
            {"action": "complete", "next_status": DouyinOrderStatus.COMPLETED},
        ],
    },
    "refund_flow": {
        "initial_order_status": DouyinOrderStatus.PAID,
        "steps": [
            {"action": "apply_refund", "next_status": DouyinOrderStatus.REFUNDING},
            {"action": "approve_refund", "next_status": DouyinOrderStatus.REFUNDED},
        ],
    },
}


def validate_status_transition(current: DouyinOrderStatus, next_status: DouyinOrderStatus) -> bool:
    allowed = DOUYIN_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: DouyinOrderStatus) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "status": status.value,
        "total_amount": "99.99",
        "pay_amount": "99.99",
        "postage_amount": "0.00",
        "receiver": {
            "name": "李四",
            "phone": "13900139000",
            "address": "上海市浦东新区",
        },
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-29T12:00:00+08:00",
    }


def get_default_refund_payload(order_id: str, refund_id: str, status: DouyinRefundStatus) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": status.value,
        "refund_amount": "50.00",
        "reason": "商品破损",
        "description": "商品在运输过程中破损",
        "created_at": "2026-03-20T10:00:00+08:00",
        "updated_at": "2026-03-29T12:00:00+08:00",
    }


def get_default_push_payload(event_type: str, order_id: str) -> Dict[str, Any]:
    push_templates = {
        "order.PaySuccess": {
            "event_type": "order.PaySuccess",
            "order_id": order_id,
            "pay_time": "2026-03-01T10:05:00+08:00",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "order.ShipSent": {
            "event_type": "order.ShipSent",
            "order_id": order_id,
            "logistics_company": "中通快递",
            "tracking_no": "ZT1234567890",
            "ship_time": "2026-03-15T14:00:00+08:00",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "order.ConfirmReceived": {
            "event_type": "order.ConfirmReceived",
            "order_id": order_id,
            "confirm_time": "2026-03-20T16:00:00+08:00",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "refund.RefundSuccess": {
            "event_type": "refund.RefundSuccess",
            "order_id": order_id,
            "refund_id": "REFUND_DY001",
            "refund_amount": "50.00",
            "refund_time": "2026-03-29T14:00:00+08:00",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
    }
    return push_templates.get(event_type, {"event_type": event_type, "order_id": order_id})


def generate_sign(params: Dict[str, Any], app_secret: str) -> str:
    import hashlib
    sorted_keys = sorted(params.keys())
    sign_str = "&".join([f"{k}={params[k]}" for k in sorted_keys])
    sign_str += f"&secret={app_secret}"
    return hashlib.md5(sign_str.encode()).hexdigest()


def verify_sign(params: Dict[str, Any], sign: str, app_secret: str) -> bool:
    expected_sign = generate_sign(params, app_secret)
    return sign == expected_sign
