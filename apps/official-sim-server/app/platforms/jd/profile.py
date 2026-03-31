from typing import Dict, Any, List, Optional
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from providers.utils.fixture_loader import FixtureLoader


class JdOrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    WAIT_SELLER_DELIVERY = "wait_seller_delivery"
    WAIT_BUYER_RECEIVE = "wait_buyer_receive"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    REFUNDING = "refunding"
    REFUNDED = "refunded"


class JdShipmentStatus(str, Enum):
    CREATED = "created"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    SIGNED = "signed"


class JdRefundStatus(str, Enum):
    NO_REFUND = "no_refund"
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDING = "refunding"
    REFUNDED = "refunded"


JD_ORDER_STATUS_TRANSITIONS: Dict[JdOrderStatus, List[JdOrderStatus]] = {
    JdOrderStatus.CREATED: [JdOrderStatus.PAID, JdOrderStatus.CANCELLED],
    JdOrderStatus.PAID: [JdOrderStatus.WAIT_SELLER_DELIVERY, JdOrderStatus.REFUNDING],
    JdOrderStatus.WAIT_SELLER_DELIVERY: [JdOrderStatus.WAIT_BUYER_RECEIVE, JdOrderStatus.REFUNDING],
    JdOrderStatus.WAIT_BUYER_RECEIVE: [JdOrderStatus.FINISHED, JdOrderStatus.REFUNDING],
    JdOrderStatus.FINISHED: [JdOrderStatus.REFUNDING],
    JdOrderStatus.CANCELLED: [],
    JdOrderStatus.REFUNDING: [JdOrderStatus.REFUNDED, JdOrderStatus.CANCELLED],
    JdOrderStatus.REFUNDED: [],
}


ORDER_SCENARIOS = {
    "basic_order": {
        "initial_order_status": JdOrderStatus.CREATED,
        "steps": [
            {"action": "pay", "next_status": JdOrderStatus.PAID},
        ],
    },
    "full_flow": {
        "initial_order_status": JdOrderStatus.CREATED,
        "steps": [
            {"action": "pay", "next_status": JdOrderStatus.PAID},
            {"action": "ship", "next_status": JdOrderStatus.WAIT_BUYER_RECEIVE},
            {"action": "receive", "next_status": JdOrderStatus.FINISHED},
        ],
    },
    "refund_flow": {
        "initial_order_status": JdOrderStatus.PAID,
        "steps": [
            {"action": "apply_refund", "next_status": JdOrderStatus.REFUNDING},
            {"action": "approve_refund", "next_status": JdOrderStatus.REFUNDED},
        ],
    },
}


SHIPMENT_SCENARIOS = {
    "basic_shipment": {
        "initial_shipment_status": JdShipmentStatus.CREATED,
        "steps": [
            {"action": "ship", "next_status": JdShipmentStatus.SHIPPED},
            {"action": "in_transit", "next_status": JdShipmentStatus.IN_TRANSIT},
            {"action": "deliver", "next_status": JdShipmentStatus.DELIVERED},
            {"action": "sign", "next_status": JdShipmentStatus.SIGNED},
        ],
    },
}


STATUS_TO_SCENARIO = {
    JdOrderStatus.CREATED: "order_created",
    JdOrderStatus.PAID: "order_paid",
    JdOrderStatus.WAIT_SELLER_DELIVERY: "order_paid",
    JdOrderStatus.WAIT_BUYER_RECEIVE: "order_shipped",
    JdOrderStatus.FINISHED: "order_finished",
    JdOrderStatus.CANCELLED: "order_cancelled",
    JdOrderStatus.REFUNDING: "order_paid",
    JdOrderStatus.REFUNDED: "order_finished",
}


def validate_status_transition(current: JdOrderStatus, next_status: JdOrderStatus) -> bool:
    allowed = JD_ORDER_STATUS_TRANSITIONS.get(current, [])
    return next_status in allowed


def get_default_order_payload(order_id: str, status: JdOrderStatus) -> Dict[str, Any]:
    scenario_key = STATUS_TO_SCENARIO.get(status, "order_paid")
    fixture = FixtureLoader.get_response("jd", scenario_key)
    data = fixture.get("jingdong_order_search_responce", {})
    return {
        "order_id": order_id,
        "status": status.value,
        "total_amount": str(data.get("orderTotalPrice", 0) / 100),
        "pay_amount": str(data.get("orderPayment", 0) / 100),
        "freight": str(data.get("freightPrice", 0) / 100),
        "receiver": {
            "name": data.get("receiverName", "王五"),
            "phone": data.get("receiverPhone", "13700137000"),
            "address": f"{data.get('province', '')}{data.get('city', '')}{data.get('county', '')}{data.get('addressDetail', '')}",
        },
        "vender_id": data.get("popVenderId", "JD_VENDER_001"),
        "order_type": "B2C",
        "created_at": data.get("orderStartTime", "2026-03-01T10:00:00+08:00"),
        "updated_at": data.get("orderStatusTime", "2026-03-29T12:00:00+08:00"),
        "_raw_fixture": fixture,
    }


def get_default_shipment_payload(order_id: str, shipment_id: str, status: JdShipmentStatus) -> Dict[str, Any]:
    fixture = FixtureLoader.get_response("jd", "order_shipped")
    data = fixture.get("jingdong_order_search_responce", {})
    return {
        "order_id": order_id,
        "shipment_id": shipment_id,
        "status": status.value,
        "logistics_company": data.get("deliveryCarrierName", "京东物流"),
        "tracking_no": data.get("deliveryBillNo", "JD1234567890"),
        "shipped_at": data.get("orderStatusTime", "2026-03-15T14:00:00+08:00"),
        "delivered_at": data.get("deliveryConfirmTime"),
        "nodes": [
            {
                "node": "已发货",
                "time": "2026-03-15T14:00:00+08:00",
                "description": "包裹已从京东仓库发出",
            },
            {
                "node": "运输中",
                "time": "2026-03-16T08:00:00+08:00",
                "description": "包裹正在运输途中",
            },
            {
                "node": "派送中",
                "time": "2026-03-17T10:00:00+08:00",
                "description": "快递员正在派送",
            },
        ],
    }


def get_default_refund_payload(order_id: str, refund_id: str, status: JdRefundStatus) -> Dict[str, Any]:
    fixture = FixtureLoader.get_response("jd", "refund_applied")
    result = fixture.get("jingdong_refund_apply_query_response", {}).get("result", {})
    refund = result.get("afsServiceStatus", {})
    business_steps = result.get("businessStepList", [])
    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": status.value,
        "apply_id": result.get("applyId"),
        "customer_pin": result.get("customerPin"),
        "customer_name": result.get("customerName"),
        "sku_id": result.get("skuId"),
        "sku_name": result.get("skuName"),
        "sku_num": result.get("skuNum"),
        "refund_type": result.get("refundType"),
        "refund_type_name": result.get("refundTypeName"),
        "refund_amount": str(result.get("refundAmount", 0) / 100),
        "question_desc": result.get("questionDesc"),
        "question_pics": result.get("questionPic", []),
        "return_ware_type": result.get("returnwareType"),
        "return_ware_type_name": result.get("returnwareTypeName"),
        "pick_ware_type": result.get("pickwareType"),
        "pick_ware_type_name": result.get("pickwareTypeName"),
        "province_name": result.get("provinceName"),
        "city_name": result.get("cityName"),
        "county_name": result.get("countyName"),
        "town_name": result.get("townName"),
        "address_detail": result.get("addressDetail"),
        "receive_name": result.get("receiveName"),
        "receive_mobile": result.get("receiveMobile"),
        "operator_pin": result.get("operatorPin"),
        "operator_name": result.get("operatorName"),
        "afs_service_step": refund.get("afsServiceStep"),
        "afs_service_step_name": refund.get("afsServiceStepName"),
        "express_company": refund.get("expressCompany"),
        "express_no": refund.get("expressNo"),
        "business_steps": [
            {
                "step": s.get("step"),
                "step_name": s.get("stepName"),
                "status": s.get("status"),
                "status_name": s.get("statusName"),
                "time": s.get("time"),
            }
            for s in business_steps
        ],
        "apply_time": result.get("afsApplyTime"),
        "update_time": result.get("updateTime"),
        "_raw_fixture": fixture,
    }


def get_default_push_payload(event_type: str, order_id: str) -> Dict[str, Any]:
    push_templates = {
        "order_status_changed": {
            "event_type": "order_status_changed",
            "order_id": order_id,
            "old_status": "paid",
            "new_status": "wait_seller_delivery",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "shipment_status_changed": {
            "event_type": "shipment_status_changed",
            "order_id": order_id,
            "logistics_company": "京东物流",
            "tracking_no": "JD1234567890",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
        "refund_applied": {
            "event_type": "refund_applied",
            "order_id": order_id,
            "refund_amount": "50.00",
            "reason": "七天无理由退货",
            "timestamp": "2026-03-29T12:00:00+08:00",
        },
    }
    return push_templates.get(event_type, {"event_type": event_type, "order_id": order_id})