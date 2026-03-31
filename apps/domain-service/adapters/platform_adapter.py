from typing import Dict, Any, Optional
from datetime import datetime
from models.unified import (
    UnifiedOrder,
    UnifiedAddress,
    UnifiedProduct,
    Platform,
    OrderStatus,
)


class TaobaoAdapter:
    @staticmethod
    def to_unified_order(platform_data: Dict[str, Any]) -> UnifiedOrder:
        trade = platform_data.get("trade", {})
        orders_list = platform_data.get("orders", {}).get("order", [])
        if not orders_list:
            orders_list = trade.get("orders", {}).get("order", [])

        receiver = UnifiedAddress(
            name=trade.get("receiver_name", ""),
            phone=trade.get("receiver_phone", ""),
            address=trade.get("receiver_address", ""),
        )

        products = [
            UnifiedProduct(
                product_id=str(order.get("oid", "")),
                name=order.get("title", ""),
                price=order.get("price", "0"),
                quantity=order.get("num", 1),
            )
            for order in orders_list
        ]

        status_map = {
            "wait_pay": OrderStatus.WAIT_PAY,
            "wait_ship": OrderStatus.WAIT_SHIP,
            "shipped": OrderStatus.SHIPPED,
            "trade_closed": OrderStatus.TRADE_CLOSED,
            "finished": OrderStatus.FINISHED,
            "WAIT_BUYER_PAY": OrderStatus.WAIT_PAY,
            "WAIT_SELLER_SEND_GOODS": OrderStatus.WAIT_SHIP,
            "WAIT_BUYER_CONFIRM_GOODS": OrderStatus.SHIPPED,
            "TRADE_FINISHED": OrderStatus.FINISHED,
        }

        return UnifiedOrder(
            order_id=trade.get("tid", ""),
            platform=Platform.TAOBAO,
            status=status_map.get(trade.get("status", ""), OrderStatus.WAIT_PAY),
            total_amount=trade.get("total_fee", "0"),
            pay_amount=trade.get("payment", "0"),
            receiver=receiver,
            products=products,
            created_at=datetime.fromisoformat(trade.get("created", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(trade.get("modified", datetime.now().isoformat())),
            external_order_id=trade.get("tid"),
        )

    @staticmethod
    def from_unified_order(unified: UnifiedOrder) -> Dict[str, Any]:
        return {
            "trade": {
                "tid": unified.order_id,
                "status": unified.status.value,
                "total_fee": unified.total_amount,
                "payment": unified.pay_amount,
                "receiver_name": unified.receiver.name,
                "receiver_phone": unified.receiver.phone,
                "receiver_address": unified.receiver.address,
                "created": unified.created_at.isoformat(),
                "modified": unified.updated_at.isoformat(),
            },
            "orders": {
                "order": [
                    {
                        "oid": p.product_id,
                        "title": p.name,
                        "price": p.price,
                        "num": p.quantity,
                    }
                    for p in unified.products
                ]
            },
        }


class DouyinShopAdapter:
    @staticmethod
    def to_unified_order(platform_data: Dict[str, Any]) -> UnifiedOrder:
        receiver_info = platform_data.get("receiver", {})

        receiver = UnifiedAddress(
            name=receiver_info.get("name", ""),
            phone=receiver_info.get("phone", ""),
            address=receiver_info.get("address", ""),
        )

        products = [
            UnifiedProduct(
                product_id=p.get("product_id", ""),
                name=p.get("name", ""),
                price=p.get("price", "0"),
                quantity=p.get("num", 1),
            )
            for p in platform_data.get("products", [])
        ]

        status_map = {
            "paid": OrderStatus.PAID,
            "shipped": OrderStatus.SHIPPED,
            "in_transit": OrderStatus.IN_TRANSIT,
            "finished": OrderStatus.FINISHED,
        }

        return UnifiedOrder(
            order_id=platform_data.get("order_id", ""),
            platform=Platform.DOUYIN_SHOP,
            status=status_map.get(platform_data.get("status", ""), OrderStatus.PAID),
            total_amount=platform_data.get("total_amount", "0"),
            pay_amount=platform_data.get("pay_amount", "0"),
            freight=platform_data.get("freight", "0"),
            receiver=receiver,
            products=products,
            created_at=datetime.fromisoformat(platform_data.get("create_time", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(platform_data.get("update_time", datetime.now().isoformat())),
        )

    @staticmethod
    def from_unified_order(unified: UnifiedOrder) -> Dict[str, Any]:
        return {
            "order_id": unified.order_id,
            "status": unified.status.value,
            "total_amount": unified.total_amount,
            "pay_amount": unified.pay_amount,
            "freight": unified.freight,
            "receiver": {
                "name": unified.receiver.name,
                "phone": unified.receiver.phone,
                "address": unified.receiver.address,
            },
            "products": [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "price": p.price,
                    "num": p.quantity,
                }
                for p in unified.products
            ],
            "create_time": unified.created_at.isoformat(),
            "update_time": unified.updated_at.isoformat(),
        }


class WecomKfAdapter:
    @staticmethod
    def to_unified_conversation(platform_data: Dict[str, Any]) -> Dict[str, Any]:
        from models.unified import UnifiedConversation, Platform, ConversationStatus

        return UnifiedConversation(
            conversation_id=platform_data.get("conversation_id", ""),
            platform=Platform.WECOM_KF,
            status=ConversationStatus.IN_SESSION
            if platform_data.get("status") == "in_session"
            else ConversationStatus.PENDING,
            openid=platform_data.get("openid"),
            scene=platform_data.get("scene"),
            created_at=datetime.fromisoformat(platform_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(platform_data.get("updated_at", datetime.now().isoformat())),
        )
