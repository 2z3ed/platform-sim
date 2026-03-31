import pytest
from fastapi.testclient import TestClient


def test_xhs_profile_exists():
    from app.platforms.xhs.profile import XhsOrderStatus, ORDER_SCENARIOS
    assert XhsOrderStatus.CREATED.value == "created"
    assert "basic_order" in ORDER_SCENARIOS
    assert "full_flow" in ORDER_SCENARIOS
    assert "refund_flow" in ORDER_SCENARIOS


def test_xhs_order_status_transitions():
    from app.platforms.xhs.profile import (
        XhsOrderStatus,
        XHS_ORDER_STATUS_TRANSITIONS,
        validate_status_transition,
    )
    assert XhsOrderStatus.CREATED in XHS_ORDER_STATUS_TRANSITIONS
    assert XhsOrderStatus.PAID in XHS_ORDER_STATUS_TRANSITIONS[XhsOrderStatus.CREATED]
    assert validate_status_transition(XhsOrderStatus.CREATED, XhsOrderStatus.PAID) is True
    assert validate_status_transition(XhsOrderStatus.CREATED, XhsOrderStatus.COMPLETED) is False


def test_xhs_order_payload():
    from app.platforms.xhs.profile import get_default_order_payload, XhsOrderStatus

    payload = get_default_order_payload("XHS_ORDER_001", XhsOrderStatus.PAID)
    assert payload["order_id"] == "XHS_ORDER_001"
    assert payload["status"] == "paid"
    assert "receiver" in payload
    assert payload["receiver"]["name"] == "张三"
    assert "customs" in payload


def test_xhs_refund_payload():
    from app.platforms.xhs.profile import get_default_refund_payload, XhsRefundStatus

    payload = get_default_refund_payload("XHS_ORDER_001", "XHS_REF_001", XhsRefundStatus.APPLIED)
    assert payload["order_id"] == "XHS_ORDER_001"
    assert payload["refund_id"] == "XHS_REF_001"
    assert payload["status"] == "applied"


def test_xhs_push_payload():
    from app.platforms.xhs.profile import get_default_push_payload

    payload = get_default_push_payload("order_status_changed", "XHS_ORDER_001")
    assert payload["event_type"] == "order_status_changed"
    assert payload["order_id"] == "XHS_ORDER_001"


def test_xhs_customs_detail():
    from app.platforms.xhs.profile import get_default_order_payload, XhsOrderStatus

    payload = get_default_order_payload("XHS_ORDER_001", XhsOrderStatus.PAID)
    assert "customs" in payload
    assert payload["customs"]["status"] == "declared"
    assert payload["customs"]["customs_code"] == "XHS001"


def test_xhs_basic_order_scenario():
    from app.platforms.xhs.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["basic_order"]
    assert scenario["initial_order_status"] == "created"
    assert len(scenario["steps"]) == 1
    assert scenario["steps"][0]["action"] == "pay"


def test_xhs_full_flow_scenario():
    from app.platforms.xhs.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["full_flow"]
    assert scenario["initial_order_status"] == "created"
    assert len(scenario["steps"]) == 4
    assert scenario["steps"][0]["action"] == "pay"
    assert scenario["steps"][1]["action"] == "deliver"
    assert scenario["steps"][2]["action"] == "receive"
    assert scenario["steps"][3]["action"] == "complete"


def test_xhs_refund_flow_scenario():
    from app.platforms.xhs.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["refund_flow"]
    assert scenario["initial_order_status"] == "paid"
    assert len(scenario["steps"]) == 3
