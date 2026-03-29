import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/kkk/Project/platform-sim/apps/domain-service')

from models.unified import (
    UnifiedOrder,
    UnifiedAddress,
    UnifiedProduct,
    UnifiedShipment,
    UnifiedRefund,
    Platform,
    OrderStatus,
    RefundStatus,
)
from adapters.platform_adapter import TaobaoAdapter, DouyinShopAdapter, WecomKfAdapter


def test_unified_address_model():
    addr = UnifiedAddress(
        name="张三",
        phone="138****8000",
        address="浙江省杭州市余杭区",
    )
    assert addr.name == "张三"
    assert addr.phone == "138****8000"


def test_unified_product_model():
    product = UnifiedProduct(
        product_id="PROD_001",
        name="测试商品",
        price="99.99",
        quantity=1,
    )
    assert product.product_id == "PROD_001"
    assert product.price == "99.99"


def test_unified_order_model():
    now = datetime.now()
    addr = UnifiedAddress(name="张三", phone="138****8000", address="杭州")
    product = UnifiedProduct(product_id="P001", name="商品", price="99.99")
    order = UnifiedOrder(
        order_id="ORDER_001",
        platform=Platform.TAOBAO,
        status=OrderStatus.WAIT_SHIP,
        total_amount="99.99",
        pay_amount="99.99",
        receiver=addr,
        products=[product],
        created_at=now,
        updated_at=now,
    )
    assert order.order_id == "ORDER_001"
    assert order.platform == Platform.TAOBAO
    assert order.status == OrderStatus.WAIT_SHIP


def test_taobao_adapter_to_unified():
    platform_data = {
        "trade": {
            "tid": "TB_ORDER_001",
            "status": "wait_ship",
            "total_fee": "99.99",
            "payment": "99.99",
            "receiver_name": "张三",
            "receiver_phone": "138****8000",
            "receiver_address": "杭州",
            "created": "2026-03-01 10:00:00",
            "modified": "2026-03-29 12:00:00",
        },
        "orders": {
            "order": [
                {
                    "oid": "OID_001",
                    "title": "测试商品",
                    "price": "99.99",
                    "num": 1,
                }
            ]
        },
    }
    unified = TaobaoAdapter.to_unified_order(platform_data)
    assert unified.order_id == "TB_ORDER_001"
    assert unified.platform == Platform.TAOBAO
    assert unified.status == OrderStatus.WAIT_SHIP
    assert len(unified.products) == 1


def test_taobao_adapter_from_unified():
    now = datetime.now()
    addr = UnifiedAddress(name="张三", phone="138****8000", address="杭州")
    product = UnifiedProduct(product_id="P001", name="商品", price="99.99")
    order = UnifiedOrder(
        order_id="TB_ORDER_001",
        platform=Platform.TAOBAO,
        status=OrderStatus.WAIT_SHIP,
        total_amount="99.99",
        pay_amount="99.99",
        receiver=addr,
        products=[product],
        created_at=now,
        updated_at=now,
    )
    platform_data = TaobaoAdapter.from_unified_order(order)
    assert platform_data["trade"]["tid"] == "TB_ORDER_001"


def test_douyin_shop_adapter_to_unified():
    platform_data = {
        "order_id": "DS_ORDER_001",
        "status": "shipped",
        "total_amount": "99.99",
        "pay_amount": "99.99",
        "freight": "0.00",
        "receiver": {
            "name": "李四",
            "phone": "139****9000",
            "address": "上海",
        },
        "products": [
            {"product_id": "P001", "name": "商品", "price": "99.99", "num": 1}
        ],
        "create_time": "2026-03-01 10:00:00",
        "update_time": "2026-03-29 12:00:00",
    }
    unified = DouyinShopAdapter.to_unified_order(platform_data)
    assert unified.order_id == "DS_ORDER_001"
    assert unified.platform == Platform.DOUYIN_SHOP
    assert unified.status == OrderStatus.SHIPPED


def test_order_status_enum():
    assert OrderStatus.WAIT_PAY.value == "wait_pay"
    assert OrderStatus.SHIPPED.value == "shipped"
    assert OrderStatus.FINISHED.value == "finished"


def test_platform_enum():
    assert Platform.TAOBAO.value == "taobao"
    assert Platform.DOUYIN_SHOP.value == "douyin_shop"
    assert Platform.WECOM_KF.value == "wecom_kf"


def test_refund_status_enum():
    assert RefundStatus.PENDING.value == "pending"
    assert RefundStatus.APPROVED.value == "approved"
    assert RefundStatus.REFUNDING.value == "refunding"
