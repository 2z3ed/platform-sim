from typing import Dict, Any, List, Optional
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from providers.utils.fixture_loader import FixtureLoader


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


class TaobaoShipmentStatus(str, Enum):
    CREATED = "created"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    SIGNED = "signed"


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


STATUS_TO_SCENARIO = {
    TaobaoOrderStatus.WAIT_PAY: "trade_wait_pay",
    TaobaoOrderStatus.WAIT_SHIP: "trade_wait_ship",
    TaobaoOrderStatus.SHIPPED: "trade_shipped",
    TaobaoOrderStatus.FINISHED: "trade_finished",
    TaobaoOrderStatus.TRADE_CLOSED: "trade_wait_pay",
}

REFUND_STATUS_TO_SCENARIO = {
    TaobaoRefundStatus.NO_REFUND: "refund_requested",
    TaobaoRefundStatus.REFUNDING: "refund_requested",
    TaobaoRefundStatus.REFUND_SUCCESS: "refund_refunded",
    TaobaoRefundStatus.REFUND_CLOSED: "refund_refunded",
}


def validate_status_transition(current: TaobaoOrderStatus, next_status: TaobaoOrderStatus) -> bool:
    allowed = TAOBAO_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: TaobaoOrderStatus) -> Dict[str, Any]:
    scenario_key = STATUS_TO_SCENARIO.get(status, "trade_wait_ship")
    fixture = FixtureLoader.get_response("taobao", scenario_key)
    fixture["trade"]["tid"] = order_id
    for order in fixture.get("orders", {}).get("order", []):
        order["oid"] = f"{order_id}_{order['oid'][-1]}"
    return fixture


def get_default_shipment_payload(order_id: str, status: str) -> Dict[str, Any]:
    fixture = FixtureLoader.get_response("taobao", "trade_shipped")
    trade = fixture.get("trade", {})
    return {
        "order_id": order_id,
        "status": status,
        "company": trade.get("orders", {}).get("order", [{}])[0].get("logistics_company", "顺丰速运"),
        "tracking_no": trade.get("orders", {}).get("order", [{}])[0].get("invoice_no", "SF1234567890"),
        "shipped_at": trade.get("consign_time", "2026-03-15 14:00:00"),
        "delivered_at": None,
    }


def get_default_refund_payload(order_id: str, refund_id: str, status: TaobaoRefundStatus) -> Dict[str, Any]:
    scenario_key = REFUND_STATUS_TO_SCENARIO.get(status, "refund_requested")
    fixture = FixtureLoader.get_response("taobao", scenario_key)
    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": status.value,
        "refund_amount": fixture.get("refund", {}).get("refund_fee", "50.00"),
        "reason": fixture.get("refund", {}).get("reason", "商品损坏"),
        "created_at": fixture.get("refund", {}).get("created", "2026-03-20 10:00:00"),
        "updated_at": fixture.get("refund", {}).get("modified", "2026-03-29 12:00:00"),
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


def transform_order_facts(facts) -> Dict[str, Any]:
    """Transform normalized order facts into Taobao platform payload."""
    status_map = {
        "wait_pay": "WAIT_BUYER_PAY",
        "paid": "WAIT_SELLER_CONSIGN",
        "shipped": "WAIT_BUYER_CONFIRM_GOODS",
        "finished": "TRADE_FINISHED",
        "trade_closed": "TRADE_CLOSED",
    }
    tb_status = status_map.get(facts.status, facts.status)

    fixture = FixtureLoader.get_response("taobao", STATUS_TO_SCENARIO.get(TaobaoOrderStatus.WAIT_SHIP, "trade_wait_ship"))
    trade = fixture.get("trade", {})
    trade["tid"] = facts.order_id
    trade["status"] = tb_status
    trade["payment"] = str(facts.total_amount)
    trade["total_fee"] = str(facts.total_amount)
    trade["buyer_nick"] = facts.receiver.name or "tb_buyer"
    trade["receiver_name"] = facts.receiver.name
    trade["receiver_mobile"] = facts.receiver.phone
    trade["receiver_state"] = ""
    trade["receiver_city"] = ""
    trade["receiver_district"] = ""
    trade["receiver_address"] = facts.receiver.address
    trade["created"] = facts.create_time
    trade["pay_time"] = facts.pay_time or ""

    orders_list = []
    for item in facts.items:
        orders_list.append({
            "oid": f"{facts.order_id}_1",
            "title": item.name,
            "num": item.quantity,
            "price": str(item.price),
            "payment": str(item.price * item.quantity),
        })
    if not orders_list:
        orders_list = [{"oid": f"{facts.order_id}_1", "title": "商品", "num": 1, "price": str(facts.total_amount), "payment": str(facts.total_amount)}]

    return {
        "trade": trade,
        "orders": {"order": orders_list},
    }


def transform_shipment_facts(facts) -> Dict[str, Any]:
    """Transform normalized shipment facts into Taobao platform payload."""
    status_map = {
        "pending": "pending",
        "in_transit": "in_transit",
        "delivered": "delivered",
        "returned": "returned",
        "cancelled": "cancelled",
    }
    tb_status = status_map.get(facts.status, "pending")

    nodes = []
    for n in facts.nodes:
        nodes.append({
            "node": n.node,
            "time": n.time,
            "description": n.description,
        })

    return {
        "order_id": facts.order_id or "",
        "status": tb_status,
        "company": facts.carrier or "顺丰速运",
        "tracking_no": facts.tracking_no or "",
        "shipped_at": facts.shipped_at or "",
        "delivered_at": facts.delivered_at or "",
        "nodes": nodes,
    }


def transform_aftersale_facts(facts) -> Dict[str, Any]:
    """Transform normalized after-sale facts into Taobao platform payload."""
    status_map = {
        "pending": "refunding",
        "approved": "approved",
        "refunded": "refunded",
        "rejected": "rejected",
    }
    tb_status = status_map.get(facts.status, "refunding")

    return {
        "order_id": facts.order_id or "",
        "refund_id": facts.after_sale_id,
        "status": tb_status,
        "status_text": "退款中" if facts.status == "pending" else "退款完成",
        "refund_type": facts.type or "退款",
        "refund_amount": str(facts.apply_amount if facts.apply_amount else 0),
        "reason": facts.reason or "",
        "apply_time": facts.created_at or "",
        "audit_time": facts.updated_at or "",
    }