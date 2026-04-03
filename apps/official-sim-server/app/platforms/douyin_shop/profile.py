from typing import Dict, Any, List, Optional
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from providers.utils.fixture_loader import FixtureLoader


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


STATUS_TO_SCENARIO = {
    DouyinOrderStatus.CREATED: "order_created",
    DouyinOrderStatus.PAID: "order_paid",
    DouyinOrderStatus.SHIPPED: "order_shipped",
    DouyinOrderStatus.CONFIRMED: "order_confirmed",
    DouyinOrderStatus.COMPLETED: "order_completed",
    DouyinOrderStatus.CANCELLED: "order_created",
    DouyinOrderStatus.REFUNDING: "order_paid",
    DouyinOrderStatus.REFUNDED: "order_completed",
}

REFUND_STATUS_TO_SCENARIO = {
    DouyinRefundStatus.APPLIED: "refund_applied",
    DouyinRefundStatus.APPROVED: "refund_approved",
    DouyinRefundStatus.REJECTED: "refund_applied",
    DouyinRefundStatus.REFUNDING: "refund_applied",
    DouyinRefundStatus.REFUNDED: "refund_approved",
    DouyinRefundStatus.CLOSED: "refund_applied",
}


def validate_status_transition(current: DouyinOrderStatus, next_status: DouyinOrderStatus) -> bool:
    allowed = DOUYIN_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: DouyinOrderStatus) -> Dict[str, Any]:
    scenario_key = STATUS_TO_SCENARIO.get(status, "order_paid")
    fixture = FixtureLoader.get_response("douyin_shop", scenario_key)
    fixture["order"]["order_id"] = order_id
    return fixture


def get_default_refund_payload(order_id: str, refund_id: str, status: DouyinRefundStatus) -> Dict[str, Any]:
    scenario_key = REFUND_STATUS_TO_SCENARIO.get(status, "refund_applied")
    fixture = FixtureLoader.get_response("douyin_shop", scenario_key)
    fixture["refund"]["order_id"] = order_id
    fixture["refund"]["refund_id"] = refund_id
    return fixture


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
            "logistics_company": "顺丰速运",
            "tracking_no": "SF1234567890",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "order.RefundSuccess": {
            "event_type": "order.RefundSuccess",
            "order_id": order_id,
            "refund_amount": "50.00",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
    }
    return push_templates.get(event_type, {"event_type": event_type, "order_id": order_id})


def transform_order_facts(facts) -> Dict[str, Any]:
    """Transform normalized order facts into Douyin Shop platform payload."""
    status_map = {
        "wait_pay": "10",
        "paid": "20",
        "shipped": "30",
        "finished": "40",
        "trade_closed": "50",
    }
    dy_status = status_map.get(facts.status, "10")

    fixture = FixtureLoader.get_response("douyin_shop", "order_paid")
    order = fixture.get("order", {})
    order["order_id"] = facts.order_id
    order["order_status"] = dy_status
    order["order_amount"] = str(facts.total_amount)
    order["pay_amount"] = str(facts.payment_amount)
    order["pay_time"] = facts.pay_time or ""
    order["create_time"] = facts.create_time

    receiver = order.get("receiver", {})
    receiver["name"] = facts.receiver.name
    receiver["phone"] = facts.receiver.phone
    receiver["address"] = facts.receiver.address
    order["receiver"] = receiver

    product_items = []
    for item in facts.items:
        product_items.append({
            "product_id": f"DY_{item.name[:10]}",
            "name": item.name,
            "price": str(item.price),
            "quantity": item.quantity,
        })
    if not product_items:
        product_items = [{"product_id": "DY_ITEM", "name": "商品", "price": str(facts.total_amount), "quantity": 1}]
    order["product_items"] = product_items

    return {"order": order}


def transform_shipment_facts(facts) -> Dict[str, Any]:
    """Transform normalized shipment facts into Douyin Shop platform payload."""
    status_map = {
        "pending": "pending",
        "in_transit": "shipped",
        "delivered": "delivered",
        "returned": "returned",
        "cancelled": "cancelled",
    }
    dy_status = status_map.get(facts.status, "pending")

    nodes = []
    for n in facts.nodes:
        nodes.append({
            "node": n.node,
            "time": n.time,
            "description": n.description,
        })

    return {
        "order_id": facts.order_id or "",
        "shipment_id": facts.shipment_id,
        "status": dy_status,
        "logistics_company": facts.carrier or "",
        "tracking_no": facts.tracking_no or "",
        "shipped_at": facts.shipped_at or "",
        "delivered_at": facts.delivered_at or "",
        "nodes": nodes,
    }


def transform_aftersale_facts(facts) -> Dict[str, Any]:
    """Transform normalized after-sale facts into Douyin Shop platform payload."""
    status_map = {
        "pending": "refunding",
        "approved": "refund_success",
        "refunded": "refund_success",
        "rejected": "refund_rejected",
    }
    dy_status = status_map.get(facts.status, "refunding")

    return {
        "order_id": facts.order_id or "",
        "after_sale_id": facts.after_sale_id,
        "status": dy_status,
        "refund_type": facts.type or "退款",
        "refund_amount": str(facts.apply_amount if facts.apply_amount else 0),
        "reason": facts.reason or "",
        "apply_time": facts.created_at or "",
        "update_time": facts.updated_at or "",
    }