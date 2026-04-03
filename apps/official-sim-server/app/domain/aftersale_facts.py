"""
Normalized after-sale facts for official-sim-server.

This is the intermediate layer between raw data sources (fixture / Odoo)
and platform profile transformers.

Raw Odoo / fixture → normalized after-sale facts → platform profile payload
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class NormalizedAfterSaleFacts:
    """Normalized after-sale facts - internal intermediate representation."""
    after_sale_id: str
    order_id: Optional[str]  # May be empty if not reliably available
    status: str  # normalized: pending / approved / rejected / refunded
    type: str  # refund_type, default "refund"
    reason: str = ""
    apply_amount: float = 0.0
    approve_amount: Optional[float] = None
    created_at: str = ""
    updated_at: str = ""
    source: str = "fixture"  # "fixture" | "odoo" - internal only
    raw_json: Dict[str, Any] = field(default_factory=dict)


# Odoo account.move state → normalized after-sale status
ODOO_AFTERSALE_STATUS_MAP: Dict[str, str] = {
    "draft": "pending",
    "posted": "approved",  # posted means refund is approved/processed
    "cancel": "rejected",
}


def normalize_odoo_aftersale(raw: Dict[str, Any]) -> NormalizedAfterSaleFacts:
    """Normalize raw Odoo account.move (out_refund) to NormalizedAfterSaleFacts."""
    odoo_state = raw.get("state", "draft")
    normalized_status = ODOO_AFTERSALE_STATUS_MAP.get(odoo_state, "pending")

    # Order ID - try invoice_origin first
    order_id = raw.get("invoice_origin", "")

    # Amount
    apply_amount = float(raw.get("amount_total", 0) or 0)
    # If posted, treat as approved - use amount_total as approved amount
    approve_amount = apply_amount if normalized_status in ("approved", "refunded") else None

    # Type - default to "refund"
    aftersale_type = "refund"

    # Reason - from narration or ref (strip HTML tags)
    reason = ""
    narration = raw.get("narration", "")
    ref = raw.get("ref", "")
    if narration:
        # Strip HTML tags
        import re
        reason = re.sub(r'<[^>]+>', '', str(narration)).strip()[:200]
    elif ref:
        reason = str(ref)[:200]

    # Dates
    created_at = raw.get("create_date", "")
    updated_at = raw.get("date", "") or created_at

    return NormalizedAfterSaleFacts(
        after_sale_id=raw.get("name", ""),
        order_id=order_id or None,
        status=normalized_status,
        type=aftersale_type,
        reason=reason,
        apply_amount=apply_amount,
        approve_amount=approve_amount,
        created_at=created_at,
        updated_at=updated_at,
        source="odoo",
        raw_json=raw,
    )


def normalize_fixture_aftersale(refund_data: Dict[str, Any], order_id: str) -> NormalizedAfterSaleFacts:
    """Normalize fixture refund data to NormalizedAfterSaleFacts."""
    status = refund_data.get("status", "pending")
    
    # Map fixture status to normalized
    fixture_status_map = {
        "pending": "pending",
        "refunding": "pending",
        "processing": "pending",
        "approved": "approved",
        "refunded": "refunded",
        "rejected": "rejected",
        "cancelled": "rejected",
    }
    normalized_status = fixture_status_map.get(status, "pending")

    # Amount
    apply_amount = float(refund_data.get("amount", 0) or 0)
    approve_amount = float(refund_data.get("approve_amount", 0) or 0) or None

    # Reason
    reason = refund_data.get("reason", "")

    # Type - default from fixture
    aftersale_type = refund_data.get("type", "refund")

    # Dates
    created_at = refund_data.get("apply_time", "")

    return NormalizedAfterSaleFacts(
        after_sale_id=refund_data.get("refund_id", ""),
        order_id=order_id,
        status=normalized_status,
        type=aftersale_type,
        reason=reason,
        apply_amount=apply_amount,
        approve_amount=approve_amount,
        created_at=created_at,
        updated_at="",
        source="fixture",
        raw_json=refund_data,
    )