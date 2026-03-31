import pytest
from providers.taobao.provider import TaobaoProvider
from providers.base.provider import ProviderMode


def test_taobao_provider_mock_mode():
    provider = TaobaoProvider(ProviderMode.MOCK)
    assert provider.is_mock() is True
    assert provider.is_real() is False


def test_taobao_get_order_mock():
    provider = TaobaoProvider(ProviderMode.MOCK)
    result = provider.get_order("TB_ORDER_001")
    assert result["trade"]["tid"] == "TB_ORDER_001"
    assert result["trade"]["status"] == "WAIT_SELLER_SEND_GOODS"


def test_taobao_list_orders_mock():
    provider = TaobaoProvider(ProviderMode.MOCK)
    result = provider.list_orders(page=1, page_size=10)
    assert "trades_sold_get_response" in result
    trades = result["trades_sold_get_response"]["trades"]["trade"]
    assert len(trades) == 10
    assert result["trades_sold_get_response"]["total_results"] == 100


def test_taobao_get_shipment_mock():
    provider = TaobaoProvider(ProviderMode.MOCK)
    result = provider.get_shipment("TB_ORDER_001")
    assert result["sid"] == "SID_TB_ORDER_001"
    assert result["status"] == "shipped"


def test_taobao_get_refund_mock():
    provider = TaobaoProvider(ProviderMode.MOCK)
    result = provider.get_refund("REFUND_001")
    assert result["refund_id"] == "REFUND_001"
    assert result["status"] == "WAIT_SELLER_AGREE"


def test_taobao_create_refund_mock():
    provider = TaobaoProvider(ProviderMode.MOCK)
    result = provider.create_refund("TB_ORDER_001", "商品损坏", "99.99")
    assert result["refund_id"] == "REFUND_TB_ORDER_001"
    assert result["status"] == "WAIT_SELLER_AGREE"


def test_taobao_switch_mode():
    provider = TaobaoProvider(ProviderMode.MOCK)
    provider.switch_mode(ProviderMode.REAL)
    assert provider.is_real() is True