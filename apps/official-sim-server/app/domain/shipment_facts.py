"""
Normalized shipment facts for official-sim-server.

This is the intermediate layer between raw data sources (fixture / Odoo)
and platform profile transformers.

Raw Odoo / fixture → normalized shipment facts → platform profile payload
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ShipmentNode:
    """Single shipment tracking node."""
    node: str
    time: str
    description: str = ""


@dataclass
class NormalizedShipmentFacts:
    """Normalized shipment facts - internal intermediate representation."""
    shipment_id: str
    order_id: Optional[str]  # May be empty if not reliably available
    status: str  # normalized: pending / in_transit / delivered / returned / cancelled
    carrier: str
    tracking_no: str
    shipped_at: Optional[str]
    delivered_at: Optional[str]
    nodes: List[ShipmentNode] = field(default_factory=list)
    source: str = "fixture"  # "fixture" | "odoo" - internal only
    raw_json: Dict[str, Any] = field(default_factory=dict)


# Odoo stock.picking state → normalized shipment status
ODOO_PICKING_STATUS_MAP: Dict[str, str] = {
    "draft": "pending",
    "waiting": "pending",
    "confirmed": "pending",
    "assigned": "in_transit",
    "processing": "in_transit",
    "done": "delivered",
    "cancel": "cancelled",
}


def normalize_odoo_shipment(raw: Dict[str, Any]) -> NormalizedShipmentFacts:
    """Normalize raw Odoo stock.picking to NormalizedShipmentFacts."""
    odoo_state = raw.get("state", "draft")
    normalized_status = ODOO_PICKING_STATUS_MAP.get(odoo_state, "pending")

    # Carrier info
    carrier_data = raw.get("carrier_data", {})
    carrier = carrier_data.get("name", "")
    if not carrier:
        carrier_id = raw.get("carrier_id", [])
        if isinstance(carrier_id, list) and len(carrier_id) > 1:
            carrier = str(carrier_id[1])

    # Tracking number
    tracking_no = raw.get("carrier_tracking_ref", "")

    # Dates
    scheduled_date = raw.get("scheduled_date", "")
    date_done = raw.get("date_done", "")

    # Order ID - try origin first, but may be empty
    order_id = raw.get("origin", "")

    # Nodes - minimal, empty for first version
    nodes = []

    return NormalizedShipmentFacts(
        shipment_id=raw.get("name", ""),
        order_id=order_id or None,
        status=normalized_status,
        carrier=carrier,
        tracking_no=tracking_no,
        shipped_at=scheduled_date or date_done,
        delivered_at=date_done if normalized_status == "delivered" else None,
        nodes=nodes,
        source="odoo",
        raw_json=raw,
    )


def normalize_fixture_shipment(shipment_data: Dict[str, Any], order_id: str) -> NormalizedShipmentFacts:
    """Normalize fixture shipment data to NormalizedShipmentFacts."""
    status = shipment_data.get("status", "pending")
    
    # Map fixture status to normalized
    fixture_status_map = {
        "pending": "pending",
        "created": "pending",
        "shipped": "in_transit",
        "in_transit": "in_transit",
        "delivered": "delivered",
        "signed": "delivered",
        "returned": "returned",
        "cancelled": "cancelled",
    }
    normalized_status = fixture_status_map.get(status, "pending")

    # Parse nodes
    nodes = []
    for n in shipment_data.get("nodes", []):
        nodes.append(ShipmentNode(
            node=n.get("node", ""),
            time=n.get("time", ""),
            description=n.get("description", ""),
        ))

    return NormalizedShipmentFacts(
        shipment_id=shipment_data.get("shipment_id", ""),
        order_id=order_id,
        status=normalized_status,
        carrier=shipment_data.get("company", ""),
        tracking_no=shipment_data.get("tracking_no", ""),
        shipped_at=shipment_data.get("shipped_at", ""),
        delivered_at=shipment_data.get("delivered_at", ""),
        nodes=nodes,
        source="fixture",
        raw_json=shipment_data,
    )