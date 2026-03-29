import pytest
import sys
from pathlib import Path

project_root = Path('/home/kkk/Project/platform-sim')
sys.path.insert(0, str(project_root / 'apps' / 'domain-service'))
sys.path.insert(0, str(project_root / 'providers'))

from providers.taobao.provider import TaobaoProvider
from providers.douyin_shop.provider import DouyinShopProvider
from providers.jd.provider import JdProvider
from providers.xhs.provider import XhsProvider
from providers.kuaishou.provider import KuaishouProvider
from providers.wecom_kf.provider import WecomKfProvider
from providers.base.provider import ProviderMode

from models.unified import Platform
from adapters.platform_adapter import TaobaoAdapter, DouyinShopAdapter


def test_taobao_provider_to_unified_integration():
    provider = TaobaoProvider(ProviderMode.MOCK)
    platform_data = provider.get_order("TB_ORDER_001")

    unified = TaobaoAdapter.to_unified_order(platform_data)

    assert unified.order_id == "TB_ORDER_001"
    assert unified.platform == Platform.TAOBAO
    assert unified.receiver.name == "张三"
    assert len(unified.products) == 1
    assert unified.products[0].name == "测试商品"


def test_douyin_shop_provider_to_unified_integration():
    provider = DouyinShopProvider(ProviderMode.MOCK)
    platform_data = provider.get_order("DS_ORDER_001")

    unified = DouyinShopAdapter.to_unified_order(platform_data)

    assert unified.order_id == "DS_ORDER_001"
    assert unified.platform == Platform.DOUYIN_SHOP
    assert unified.receiver.name == "李四"
    assert len(unified.products) == 1


def test_jd_provider_order_flow():
    provider = JdProvider(ProviderMode.MOCK)

    order = provider.get_order("JD_ORDER_001")
    assert order["order_id"] == "JD_ORDER_001"
    assert order["status"] == "wait_seller_delivery"

    orders = provider.list_orders(page=1, page_size=10)
    assert len(orders["order_list"]) == 10

    shipment = provider.get_shipment("JD_ORDER_001")
    assert shipment["status"] == "in_transit"

    refund = provider.get_refund("JD_REF_001")
    assert refund["status"] == "approved"


def test_xhs_provider_order_flow():
    provider = XhsProvider(ProviderMode.MOCK)

    order = provider.get_order("XHS_ORDER_001")
    assert order["order_id"] == "XHS_ORDER_001"
    assert order["status"] == "delivering"
    assert "customs" in order

    orders = provider.list_orders(page=1, page_size=10)
    assert len(orders["order_list"]) == 10

    refund = provider.create_refund("XHS_ORDER_001", "商品损坏", "149.99")
    assert refund["status"] == "applied"


def test_kuaishou_provider_order_flow():
    provider = KuaishouProvider(ProviderMode.MOCK)

    order = provider.get_order("KS_ORDER_001")
    assert order["order_id"] == "KS_ORDER_001"
    assert order["status"] == "delivered"

    orders = provider.list_orders(page=1, page_size=10)
    assert len(orders["order_list"]) == 10

    shipment = provider.get_shipment("KS_ORDER_001")
    assert shipment["status"] == "signed"


def test_wecom_kf_provider_conversation_flow():
    provider = WecomKfProvider(ProviderMode.MOCK)

    conv = provider.get_conversation("WECOM_CONV_001")
    assert conv["conversation_id"] == "WECOM_CONV_001"
    assert conv["status"] == "in_session"

    messages = provider.list_messages("WECOM_CONV_001", limit=10)
    assert "msg_list" in messages
    assert len(messages["msg_list"]) == 10


def test_provider_mode_switch():
    for cls in [TaobaoProvider, DouyinShopProvider, JdProvider, XhsProvider, KuaishouProvider]:
        provider = cls(ProviderMode.MOCK)
        assert provider.is_mock() is True

        provider.switch_mode(ProviderMode.REAL)
        assert provider.is_real() is True

        provider.switch_mode(ProviderMode.MOCK)
        assert provider.is_mock() is True


def test_unified_roundtrip_taobao():
    provider = TaobaoProvider(ProviderMode.MOCK)
    platform_data = provider.get_order("TB_ORDER_001")

    unified = TaobaoAdapter.to_unified_order(platform_data)
    back_to_platform = TaobaoAdapter.from_unified_order(unified)

    assert back_to_platform["trade"]["tid"] == "TB_ORDER_001"
    assert back_to_platform["trade"]["status"] == unified.status.value


def test_provider_refund_flow():
    for provider_cls, order_id in [
        (TaobaoProvider, "TB_ORDER_001"),
        (DouyinShopProvider, "DS_ORDER_001"),
        (JdProvider, "JD_ORDER_001"),
        (XhsProvider, "XHS_ORDER_001"),
        (KuaishouProvider, "KS_ORDER_001"),
    ]:
        provider = provider_cls(ProviderMode.MOCK)

        refund = provider.create_refund(order_id, "商品损坏", "99.99")
        assert refund["status"] in ("applied", "refunding")
        assert "refund_fee" in refund or "refund_amount" in refund

        fetched = provider.get_refund(refund["refund_id"])
        assert fetched["refund_id"] == refund["refund_id"]
