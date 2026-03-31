from typing import Dict, Any, List, Optional
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from providers.utils.fixture_loader import FixtureLoader


class XhsOrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUND_APPLIED = "refund_applied"
    REFUND_PROCESSING = "refund_processing"
    REFUND_REFUSED = "refund_refused"
    REFUNDED = "refunded"


class XhsReceiverDetail(str, Enum):
    NAME = "name"
    PHONE = "phone"
    ADDRESS = "address"
    POSTAL_CODE = "postal_code"


class XhsCustomsDetail(str, Enum):
    DECLARED = "declared"
    PASSED = "passed"
    CLEARED = "cleared"


class XhsRefundStatus(str, Enum):
    NO_REFUND = "no_refund"
    APPLIED = "applied"
    PROCESSING = "processing"
    REFUSED = "refused"
    REFUNDED = "refunded"


XHS_ORDER_STATUS_TRANSITIONS: Dict[XhsOrderStatus, List[XhsOrderStatus]] = {
    XhsOrderStatus.CREATED: [XhsOrderStatus.PAID, XhsOrderStatus.CANCELLED],
    XhsOrderStatus.PAID: [XhsOrderStatus.DELIVERING, XhsOrderStatus.REFUND_APPLIED],
    XhsOrderStatus.DELIVERING: [XhsOrderStatus.DELIVERED, XhsOrderStatus.REFUND_APPLIED],
    XhsOrderStatus.DELIVERED: [XhsOrderStatus.COMPLETED, XhsOrderStatus.REFUND_APPLIED],
    XhsOrderStatus.COMPLETED: [XhsOrderStatus.REFUND_APPLIED],
    XhsOrderStatus.CANCELLED: [],
    XhsOrderStatus.REFUND_APPLIED: [XhsOrderStatus.REFUND_PROCESSING, XhsOrderStatus.REFUND_REFUSED],
    XhsOrderStatus.REFUND_PROCESSING: [XhsOrderStatus.REFUNDED],
    XhsOrderStatus.REFUND_REFUSED: [],
}


ORDER_SCENARIOS = {
    "basic_order": {
        "initial_order_status": XhsOrderStatus.CREATED,
        "steps": [
            {"action": "pay", "next_status": XhsOrderStatus.PAID},
        ],
    },
    "full_flow": {
        "initial_order_status": XhsOrderStatus.CREATED,
        "steps": [
            {"action": "pay", "next_status": XhsOrderStatus.PAID},
            {"action": "deliver", "next_status": XhsOrderStatus.DELIVERING},
            {"action": "receive", "next_status": XhsOrderStatus.DELIVERED},
            {"action": "complete", "next_status": XhsOrderStatus.COMPLETED},
        ],
    },
    "refund_flow": {
        "initial_order_status": XhsOrderStatus.PAID,
        "steps": [
            {"action": "apply_refund", "next_status": XhsOrderStatus.REFUND_APPLIED},
            {"action": "process_refund", "next_status": XhsOrderStatus.REFUND_PROCESSING},
            {"action": "refund_success", "next_status": XhsOrderStatus.REFUNDED},
        ],
    },
}


STATUS_TO_SCENARIO = {
    XhsOrderStatus.CREATED: "order_created",
    XhsOrderStatus.PAID: "order_paid",
    XhsOrderStatus.DELIVERING: "order_delivering",
    XhsOrderStatus.DELIVERED: "order_delivering",
    XhsOrderStatus.COMPLETED: "order_completed",
    XhsOrderStatus.CANCELLED: "order_cancelled",
    XhsOrderStatus.REFUND_APPLIED: "refund_applied",
    XhsOrderStatus.REFUND_PROCESSING: "refund_applied",
    XhsOrderStatus.REFUND_REFUSED: "refund_applied",
    XhsOrderStatus.REFUNDED: "order_completed",
}


REFUND_STATUS_TO_SCENARIO = {
    XhsRefundStatus.APPLIED: "refund_applied",
    XhsRefundStatus.PROCESSING: "refund_applied",
    XhsRefundStatus.REFUSED: "refund_applied",
    XhsRefundStatus.REFUNDED: "order_completed",
}


def validate_status_transition(current: XhsOrderStatus, next_status: XhsOrderStatus) -> bool:
    allowed = XHS_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: XhsOrderStatus) -> Dict[str, Any]:
    scenario_key = STATUS_TO_SCENARIO.get(status, "order_paid")
    fixture = FixtureLoader.get_response("xhs", scenario_key)
    order = fixture.get("order", {})

    customs = order.get("customsDeclarationInfo", {})
    return {
        "order_id": order_id,
        "status": status.value,
        "total_amount": str(order.get("totalAmount", 0) / 100),
        "pay_amount": str(order.get("payAmount", 0) / 100),
        "postage": str(order.get("postAmount", 0) / 100),
        "receiver": {
            "name": order.get("receiver", {}).get("name", "赵六"),
            "phone": order.get("receiver", {}).get("phone", "13600136000"),
            "address": order.get("receiver", {}).get("fullAddress", "广州市天河区"),
        },
        "customs": {
            "customs_code": customs.get("customsDeclarationId", "XHS001"),
            "declared_at": customs.get("declarationTime", "2026-03-10T10:00:00+08:00"),
            "cleared_at": customs.get("clearanceTime"),
            "status": customs.get("customsStatus", "declared"),
        },
        "_raw_fixture": fixture,
    }


def get_default_refund_payload(order_id: str, refund_id: str, status: XhsRefundStatus) -> Dict[str, Any]:
    scenario_key = REFUND_STATUS_TO_SCENARIO.get(status, "refund_applied")
    fixture = FixtureLoader.get_response("xhs", scenario_key)
    refund = fixture.get("refund", fixture.get("response", {}).get("refund", {}))
    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": status.value,
        "refund_amount": str(refund.get("refundAmount", refund.get("refund_amount", 5000)) / 100),
        "reason": refund.get("reason", "商品不满意"),
        "apply_time": refund.get("applyTime", refund.get("apply_time", "2026-03-20T10:00:00+08:00")),
        "update_time": refund.get("updateTime", refund.get("update_time", "2026-03-29T12:00:00+08:00")),
    }


def get_default_push_payload(event_type: str, order_id: str) -> Dict[str, Any]:
    push_templates = {
        "order_status_changed": {
            "event_type": "order_status_changed",
            "order_id": order_id,
            "old_status": "paid",
            "new_status": "delivering",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "refund_applied": {
            "event_type": "refund_applied",
            "order_id": order_id,
            "refund_id": "REFUND_XHS_001",
            "refund_amount": "50.00",
            "reason": "商品不满意",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "customs_cleared": {
            "event_type": "customs_cleared",
            "order_id": order_id,
            "customs_status": "cleared",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
    }
    return push_templates.get(event_type, {"event_type": event_type, "order_id": order_id})