import pytest
from fastapi.testclient import TestClient


def test_kuaishou_profile_exists():
    from app.platforms.kuaishou.profile import KuaishouOrderStatus, ORDER_SCENARIOS
    assert KuaishouOrderStatus.CREATED.value == "created"
    assert "basic_order" in ORDER_SCENARIOS
    assert "full_flow" in ORDER_SCENARIOS
    assert "refund_flow" in ORDER_SCENARIOS


def test_kuaishou_order_status_transitions():
    from app.platforms.kuaishou.profile import (
        KuaishouOrderStatus,
        KUAISHOU_ORDER_STATUS_TRANSITIONS,
        validate_status_transition,
    )
    assert KuaishouOrderStatus.CREATED in KUAISHOU_ORDER_STATUS_TRANSITIONS
    assert KuaishouOrderStatus.PAID in KUAISHOU_ORDER_STATUS_TRANSITIONS[KuaishouOrderStatus.CREATED]
    assert validate_status_transition(KuaishouOrderStatus.CREATED, KuaishouOrderStatus.PAID) is True
    assert validate_status_transition(KuaishouOrderStatus.CREATED, KuaishouOrderStatus.FINISHED) is False


def test_kuaishou_order_payload():
    from app.platforms.kuaishou.profile import get_default_order_payload, KuaishouOrderStatus

    payload = get_default_order_payload("KS_ORDER_001", KuaishouOrderStatus.PAID)
    assert payload["order_id"] == "KS_ORDER_001"
    assert payload["status"] == "paid"
    assert "receiver" in payload
    assert payload["receiver"]["name"] == "张三"
    assert payload["shop_name"] == "快手小店"


def test_kuaishou_logistics_payload():
    from app.platforms.kuaishou.profile import (
        get_default_logistics_payload,
        KuaishouLogisticsStatus,
    )

    payload = get_default_logistics_payload(
        "KS_ORDER_001", "KS_LOG_001", KuaishouLogisticsStatus.IN_TRANSIT
    )
    assert payload["order_id"] == "KS_ORDER_001"
    assert payload["logistics_id"] == "KS_LOG_001"
    assert payload["status"] == "in_transit"
    assert "nodes" in payload
    assert len(payload["nodes"]) == 3


def test_kuaishou_refund_payload():
    from app.platforms.kuaishou.profile import get_default_refund_payload, KuaishouRefundStatus

    payload = get_default_refund_payload("KS_ORDER_001", "KS_REF_001", KuaishouRefundStatus.APPLIED)
    assert payload["order_id"] == "KS_ORDER_001"
    assert payload["refund_id"] == "KS_REF_001"
    assert payload["status"] == "applied"
    assert payload["refund_amount"] == "99.99"


def test_kuaishou_push_payload():
    from app.platforms.kuaishou.profile import get_default_push_payload

    payload = get_default_push_payload("order_status_changed", "KS_ORDER_001")
    assert payload["event_type"] == "order_status_changed"
    assert payload["order_id"] == "KS_ORDER_001"


def test_kuaishou_basic_order_scenario():
    from app.platforms.kuaishou.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["basic_order"]
    assert scenario["initial_order_status"] == "created"
    assert len(scenario["steps"]) == 1
    assert scenario["steps"][0]["action"] == "pay"


def test_kuaishou_full_flow_scenario():
    from app.platforms.kuaishou.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["full_flow"]
    assert scenario["initial_order_status"] == "created"
    assert len(scenario["steps"]) == 4
    assert scenario["steps"][0]["action"] == "pay"
    assert scenario["steps"][1]["action"] == "deliver"
    assert scenario["steps"][2]["action"] == "confirm"
    assert scenario["steps"][3]["action"] == "finish"


def test_kuaishou_refund_flow_scenario():
    from app.platforms.kuaishou.profile import ORDER_SCENARIOS

    scenario = ORDER_SCENARIOS["refund_flow"]
    assert scenario["initial_order_status"] == "paid"
    assert len(scenario["steps"]) == 3
