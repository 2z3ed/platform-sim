"""
Normalized order facts for official-sim-server.

This is the intermediate layer between raw data sources (fixture / Odoo)
and platform profile transformers.

Raw Odoo / fixture → normalized facts → platform profile payload
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class OrderItem:
    name: str
    quantity: int
    price: float


@dataclass
class Receiver:
    name: str
    phone: str
    address: str


@dataclass
class NormalizedOrderFacts:
    """Normalized order facts - internal intermediate representation."""
    order_id: str
    status: str  # normalized: wait_pay / paid / finished / trade_closed
    total_amount: float
    payment_amount: float
    currency: str
    create_time: str
    pay_time: Optional[str]
    receiver: Receiver
    items: List[OrderItem]
    source: str = "fixture"  # "fixture" | "odoo" - internal only
    raw_json: Dict[str, Any] = field(default_factory=dict)


# Odoo sale.order state → normalized status
ODOO_STATUS_MAP: Dict[str, str] = {
    "draft": "wait_pay",
    "sent": "wait_pay",
    "sale": "paid",
    "done": "finished",
    "cancel": "trade_closed",
}


def normalize_odoo_order(raw: Dict[str, Any]) -> NormalizedOrderFacts:
    """Normalize raw Odoo sale.order to NormalizedOrderFacts."""
    odoo_status = raw.get("state", "draft")
    normalized_status = ODOO_STATUS_MAP.get(odoo_status, "wait_pay")

    total_amount = float(raw.get("amount_total", 0) or 0)
    # Odoo may not have stable amount_paid; derive from payment state
    amount_paid = raw.get("amount_paid")
    if amount_paid is not None:
        payment_amount = float(amount_paid)
    elif normalized_status in ("paid", "finished"):
        payment_amount = total_amount
    else:
        payment_amount = 0.0

    # Try to get shipping partner data
    shipping_data = raw.get("partner_shipping_data")
    if shipping_data:
        receiver_name = shipping_data.get("name", "")
        receiver_phone = shipping_data.get("phone", "") or shipping_data.get("mobile", "") or ""
        
        # Build address from partner fields
        address_parts = []
        for key in ("street", "street2", "city", "state_id", "zip"):
            val = shipping_data.get(key)
            if val:
                if isinstance(val, list) and len(val) > 1:
                    address_parts.append(str(val[1]))
                elif val:
                    address_parts.append(str(val))
        receiver_address = ", ".join(address_parts) if address_parts else ""
    else:
        # Fallback: try partner_shipping_id as [id, name] format
        shipping = raw.get("partner_shipping_id", [])
        if isinstance(shipping, list) and len(shipping) > 1:
            receiver_name = str(shipping[1])
        else:
            receiver_name = ""
        receiver_phone = ""
        receiver_address = ""

    # Line items
    items = []
    for line in raw.get("order_line", []):
        if isinstance(line, dict):
            items.append(OrderItem(
                name=line.get("name", ""),
                quantity=int(line.get("product_uom_qty", 0) or 0),
                price=float(line.get("price_unit", 0) or 0),
            ))

    return NormalizedOrderFacts(
        order_id=raw.get("name", raw.get("client_order_ref", "")),
        status=normalized_status,
        total_amount=total_amount,
        payment_amount=payment_amount,
        currency=raw.get("currency_id", ["", "CNY"])[1] if isinstance(raw.get("currency_id"), list) else "CNY",
        create_time=raw.get("create_date", ""),
        pay_time=raw.get("date_order", ""),
        receiver=Receiver(
            name=receiver_name,
            phone=receiver_phone,
            address=receiver_address,
        ),
        items=items,
        source="odoo",
        raw_json=raw,
    )


def normalize_fixture_order(platform: str, order_data: Dict[str, Any]) -> NormalizedOrderFacts:
    """Normalize fixture order data to NormalizedOrderFacts."""
    status = order_data.get("status", "unknown")
    amount = float(order_data.get("amount", 0) or 0)

    receiver_data = order_data.get("receiver", {})
    receiver = Receiver(
        name=receiver_data.get("name", ""),
        phone=receiver_data.get("phone", ""),
        address=receiver_data.get("address", ""),
    )

    items = []
    for item in order_data.get("items", []):
        items.append(OrderItem(
            name=item.get("name", ""),
            quantity=int(item.get("quantity", 0) or 0),
            price=float(item.get("price", 0) or 0),
        ))

    return NormalizedOrderFacts(
        order_id=order_data.get("order_id", ""),
        status=status,
        total_amount=amount,
        payment_amount=amount,  # fixture: assume fully paid
        currency="CNY",
        create_time=order_data.get("created_at", ""),
        pay_time=order_data.get("paid_at", ""),
        receiver=receiver,
        items=items,
        source="fixture",
        raw_json=order_data,
    )
