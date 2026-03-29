import pytest
import sys
from pathlib import Path

sys.path.insert(0, '/home/kkk/Project/platform-sim')

from providers.jd.provider import JdProvider
from providers.xhs.provider import XhsProvider
from providers.kuaishou.provider import KuaishouProvider
from providers.base.provider import ProviderMode


def test_jd_provider_mock_mode():
    provider = JdProvider(ProviderMode.MOCK)
    assert provider.is_mock() is True


def test_jd_get_order_mock():
    provider = JdProvider(ProviderMode.MOCK)
    result = provider.get_order("JD_ORDER_001")
    assert result["order_id"] == "JD_ORDER_001"
    assert result["status"] == "wait_seller_delivery"


def test_jd_list_orders_mock():
    provider = JdProvider(ProviderMode.MOCK)
    result = provider.list_orders(page=1, page_size=10)
    assert "order_list" in result
    assert len(result["order_list"]) == 10


def test_jd_get_shipment_mock():
    provider = JdProvider(ProviderMode.MOCK)
    result = provider.get_shipment("JD_ORDER_001")
    assert result["order_id"] == "JD_ORDER_001"
    assert result["status"] == "in_transit"


def test_jd_get_refund_mock():
    provider = JdProvider(ProviderMode.MOCK)
    result = provider.get_refund("JD_REF_001")
    assert result["refund_id"] == "JD_REF_001"
    assert result["status"] == "approved"


def test_xhs_provider_mock_mode():
    provider = XhsProvider(ProviderMode.MOCK)
    assert provider.is_mock() is True


def test_xhs_get_order_mock():
    provider = XhsProvider(ProviderMode.MOCK)
    result = provider.get_order("XHS_ORDER_001")
    assert result["order_id"] == "XHS_ORDER_001"
    assert result["status"] == "delivering"


def test_xhs_list_orders_mock():
    provider = XhsProvider(ProviderMode.MOCK)
    result = provider.list_orders(page=1, page_size=10)
    assert "order_list" in result
    assert len(result["order_list"]) == 10


def test_xhs_get_shipment_mock():
    provider = XhsProvider(ProviderMode.MOCK)
    result = provider.get_shipment("XHS_ORDER_001")
    assert result["order_id"] == "XHS_ORDER_001"
    assert result["status"] == "in_transit"


def test_kuaishou_provider_mock_mode():
    provider = KuaishouProvider(ProviderMode.MOCK)
    assert provider.is_mock() is True


def test_kuaishou_get_order_mock():
    provider = KuaishouProvider(ProviderMode.MOCK)
    result = provider.get_order("KS_ORDER_001")
    assert result["order_id"] == "KS_ORDER_001"
    assert result["status"] == "delivered"


def test_kuaishou_list_orders_mock():
    provider = KuaishouProvider(ProviderMode.MOCK)
    result = provider.list_orders(page=1, page_size=10)
    assert "order_list" in result
    assert len(result["order_list"]) == 10


def test_kuaishou_get_shipment_mock():
    provider = KuaishouProvider(ProviderMode.MOCK)
    result = provider.get_shipment("KS_ORDER_001")
    assert result["order_id"] == "KS_ORDER_001"
    assert result["status"] == "signed"


def test_all_providers_switch_mode():
    for cls in [JdProvider, XhsProvider, KuaishouProvider]:
        provider = cls(ProviderMode.MOCK)
        provider.switch_mode(ProviderMode.REAL)
        assert provider.is_real() is True
