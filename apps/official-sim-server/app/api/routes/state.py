"""
State management API for official-sim-server.

Handles:
- State advance for order / shipment / after_sale
- State query
- Event query
- Error injection
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.domain.state_machine import state_machine, TransitionError
from app.domain.error_injector import error_injector
from app.domain.event_log import event_log
from app.domain.push_delivery import push_delivery_manager
from app.core.config import settings
from app.platforms.taobao.profile import (
    TaobaoOrderStatus, TaobaoShipmentStatus, TaobaoRefundStatus,
    TAOBAO_ORDER_STATUS_TRANSITIONS, get_default_order_payload as tb_order_payload,
    get_default_shipment_payload as tb_shipment_payload,
    get_default_refund_payload as tb_refund_payload,
    validate_status_transition as tb_validate,
)
from app.platforms.douyin_shop.profile import (
    DouyinOrderStatus, DouyinRefundStatus,
    DOUYIN_ORDER_STATUS_TRANSITIONS, get_default_order_payload as dy_order_payload,
    get_default_refund_payload as dy_refund_payload,
    validate_status_transition as dy_validate,
)
from app.platforms.jd.profile import (
    JdOrderStatus, JdShipmentStatus, JdRefundStatus,
    JD_ORDER_STATUS_TRANSITIONS, get_default_order_payload as jd_order_payload,
    get_default_shipment_payload as jd_shipment_payload,
    get_default_refund_payload as jd_refund_payload,
    validate_status_transition as jd_validate,
)

router = APIRouter()


# Status maps for each platform
ORDER_STATUS_ENUMS = {
    "taobao": TaobaoOrderStatus,
    "douyin_shop": DouyinOrderStatus,
    "jd": JdOrderStatus,
}
ORDER_TRANSITIONS = {
    "taobao": TAOBAO_ORDER_STATUS_TRANSITIONS,
    "douyin_shop": DOUYIN_ORDER_STATUS_TRANSITIONS,
    "jd": JD_ORDER_STATUS_TRANSITIONS,
}
VALIDATE_FNS = {
    "taobao": tb_validate,
    "douyin_shop": dy_validate,
    "jd": jd_validate,
}
SHIPMENT_STATUS_ENUMS = {
    "taobao": TaobaoShipmentStatus,
    "jd": JdShipmentStatus,
}
REFUND_STATUS_ENUMS = {
    "taobao": TaobaoRefundStatus,
    "douyin_shop": DouyinRefundStatus,
    "jd": JdRefundStatus,
}


class AdvanceRequest(BaseModel):
    action: str
    new_status: Optional[str] = None


class AdvanceResponse(BaseModel):
    success: bool
    platform: str
    resource_type: str
    resource_id: str
    before_status: str
    after_status: str
    event_id: Optional[str] = None
    push_ids: List[str] = []


class PushDetailResponse(BaseModel):
    push_id: str
    event_id: str
    platform: str
    resource_type: str
    resource_id: str
    target_url: str
    delivery_status: str
    attempt_count: int
    last_error: Optional[str] = None
    created_at: str
    updated_at: str


class ReplayPushResponse(BaseModel):
    push_id: str
    delivery_status: str
    attempt_count: int
    last_error: Optional[str] = None


class StatusResponse(BaseModel):
    platform: str
    resource_type: str
    resource_id: str
    current_status: str
    history: List[Dict[str, Any]]


class InjectErrorRequest(BaseModel):
    error_type: int
    once: bool = True
    ttl: int = 1


class InjectErrorResponse(BaseModel):
    success: bool
    platform: str
    resource_type: str
    resource_id: str
    error_type: int
    remaining: int


def _get_status_enum(platform: str, resource_type: str):
    if resource_type == "order":
        return ORDER_STATUS_ENUMS.get(platform)
    elif resource_type == "shipment":
        return SHIPMENT_STATUS_ENUMS.get(platform)
    elif resource_type == "after_sale":
        return REFUND_STATUS_ENUMS.get(platform)
    return None


def _get_transitions(platform: str, resource_type: str):
    if resource_type == "order":
        return ORDER_TRANSITIONS.get(platform, {})
    return {}


def _get_payload(platform: str, resource_type: str, resource_id: str, status: str) -> Dict[str, Any]:
    """Generate platform-specific payload for a resource at given status."""
    if resource_type == "order":
        enum_cls = ORDER_STATUS_ENUMS.get(platform)
        if not enum_cls:
            return {}
        try:
            status_enum = enum_cls(status)
        except ValueError:
            return {}
        if platform == "taobao":
            return tb_order_payload(resource_id, status_enum)
        elif platform == "douyin_shop":
            return dy_order_payload(resource_id, status_enum)
        elif platform == "jd":
            return jd_order_payload(resource_id, status_enum)
    elif resource_type == "shipment":
        enum_cls = SHIPMENT_STATUS_ENUMS.get(platform)
        if not enum_cls:
            return {}
        try:
            status_enum = enum_cls(status)
        except ValueError:
            return {}
        if platform == "taobao":
            return tb_shipment_payload(resource_id, status_enum.value if hasattr(status_enum, 'value') else str(status_enum))
        elif platform == "jd":
            return jd_shipment_payload(resource_id, f"SHIP_{resource_id}", status_enum)
    elif resource_type == "after_sale":
        enum_cls = REFUND_STATUS_ENUMS.get(platform)
        if not enum_cls:
            return {}
        try:
            status_enum = enum_cls(status)
        except ValueError:
            return {}
        refund_id = f"REF_{resource_id}"
        if platform == "taobao":
            return tb_refund_payload(resource_id, refund_id, status_enum)
        elif platform == "douyin_shop":
            return dy_refund_payload(resource_id, refund_id, status_enum)
        elif platform == "jd":
            return jd_refund_payload(resource_id, refund_id, status_enum)
    return {}


def _transform_facts_to_payload(platform: str, facts) -> Dict[str, Any]:
    """Transform normalized order facts into platform-specific payload."""
    if platform == "taobao":
        from app.platforms.taobao.profile import transform_order_facts as tb_transform
        return tb_transform(facts)
    elif platform == "douyin_shop":
        from app.platforms.douyin_shop.profile import transform_order_facts as dy_transform
        return dy_transform(facts)
    elif platform == "jd":
        from app.platforms.jd.profile import transform_order_facts as jd_transform
        return jd_transform(facts)
    return {}


def _get_event_type(resource_type: str, action: str) -> str:
    if resource_type == "order":
        return "order_status_changed"
    elif resource_type == "shipment":
        return "shipment_status_changed"
    elif resource_type == "after_sale":
        return "after_sale_status_changed"
    return "unknown"


@router.post("/{platform}/{resource_type}/{resource_id}/advance", response_model=AdvanceResponse)
async def advance_state(
    platform: str,
    resource_type: str,
    resource_id: str,
    request: AdvanceRequest,
):
    if not request.new_status:
        raise HTTPException(status_code=400, detail="new_status is required. Provide the target status explicitly.")

    # Auto-initialize state from fixture if not already done
    from app.api.routes.query import _ensure_state_initialized, FixtureLoader
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, resource_id)
            if order_data:
                _ensure_state_initialized(platform, resource_type, resource_id, order_data)
                break
        except FileNotFoundError:
            continue

    # Verify resource exists in state machine
    state = state_machine.get_state(platform, resource_type, resource_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Resource not found in fixtures: {platform}/{resource_type}/{resource_id}")

    new_status = request.new_status

    # Get platform validator and allowed transitions for this resource type
    validate_fn = VALIDATE_FNS.get(platform) if resource_type == "order" else None
    transitions = _get_transitions(platform, resource_type)

    # Build allowed status list for error messages
    current_state = state_machine.get_state(platform, resource_type, resource_id)
    allowed_statuses = []
    if current_state and transitions:
        try:
            status_enum = ORDER_STATUS_ENUMS.get(platform)
            if status_enum:
                current_enum = status_enum(current_state.current_status)
                allowed = transitions.get(current_enum, [])
                allowed_statuses = [s.value if hasattr(s, 'value') else str(s) for s in allowed]
        except ValueError:
            pass

    # Advance state with validation
    try:
        result = state_machine.advance(
            platform, resource_type, resource_id,
            new_status, request.action,
            validate_fn=validate_fn,
            allowed_statuses=allowed_statuses,
        )
    except TransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail=f"Resource not found: {platform}/{resource_type}/{resource_id}")

    # Generate event with platform-specific payload
    payload = _get_payload(platform, resource_type, resource_id, new_status)
    event_type = _get_event_type(resource_type, request.action)
    event = event_log.record(
        event_type=event_type,
        platform=platform,
        resource_type=resource_type,
        resource_id=resource_id,
        before_status=result["before_status"],
        after_status=result["after_status"],
        payload=payload,
    )

    # Create push delivery records for configured webhook URLs
    webhook_urls = settings.get_webhook_urls()
    push_deliveries = []
    for url in webhook_urls:
        push_payload = {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "occurred_at": event["occurred_at"],
            "payload": payload,
        }
        delivery = push_delivery_manager.create(
            event_id=event["event_id"],
            platform=platform,
            resource_type=resource_type,
            resource_id=resource_id,
            target_url=url,
            payload=push_payload,
        )
        # Attempt delivery immediately
        try:
            push_delivery_manager.attempt_delivery(delivery.push_id)
        except Exception:
            pass  # Push failure doesn't break the event
        push_deliveries.append(delivery.push_id)

    return AdvanceResponse(
        success=True,
        platform=platform,
        resource_type=resource_type,
        resource_id=resource_id,
        before_status=result["before_status"],
        after_status=result["after_status"],
        event_id=event["event_id"],
        push_ids=push_deliveries,
    )


@router.get("/{platform}/{resource_type}/{resource_id}/status", response_model=StatusResponse)
async def get_status(platform: str, resource_type: str, resource_id: str):
    state = state_machine.get_state(platform, resource_type, resource_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Resource not found: {platform}/{resource_type}/{resource_id}")
    return StatusResponse(
        platform=state.platform,
        resource_type=state.resource_type,
        resource_id=state.resource_id,
        current_status=state.current_status,
        history=state.history,
    )


@router.get("/{platform}/{resource_type}/{resource_id}/events")
async def get_events(platform: str, resource_type: str, resource_id: str):
    events = event_log.get_events_for_resource(platform, resource_type, resource_id)
    return {"events": events, "total": len(events)}


@router.post("/{platform}/{resource_type}/{resource_id}/inject-error", response_model=InjectErrorResponse)
async def inject_error(
    platform: str,
    resource_type: str,
    resource_id: str,
    request: InjectErrorRequest,
):
    injection = error_injector.inject(
        platform=platform,
        resource_type=resource_type,
        resource_id=resource_id,
        error_type=request.error_type,
        once=request.once,
        ttl=request.ttl,
    )
    return InjectErrorResponse(
        success=True,
        platform=platform,
        resource_type=resource_type,
        resource_id=resource_id,
        error_type=request.error_type,
        remaining=injection.remaining,
    )


@router.get("/{platform}/{resource_type}/{resource_id}/pushes")
async def get_pushes(platform: str, resource_type: str, resource_id: str):
    deliveries = push_delivery_manager.list_by_resource(platform, resource_type, resource_id)
    return {
        "pushes": [d.to_dict() for d in deliveries],
        "total": len(deliveries),
    }


@router.get("/push/{push_id}", response_model=PushDetailResponse)
async def get_push_detail(push_id: str):
    delivery = push_delivery_manager.get(push_id)
    if not delivery:
        raise HTTPException(status_code=404, detail=f"Push delivery {push_id} not found")
    return PushDetailResponse(**delivery.to_dict())


@router.post("/push/{push_id}/replay", response_model=ReplayPushResponse)
async def replay_push(push_id: str):
    try:
        delivery = push_delivery_manager.replay(push_id)
        return ReplayPushResponse(
            push_id=delivery.push_id,
            delivery_status=delivery.delivery_status,
            attempt_count=delivery.attempt_count,
            last_error=delivery.last_error,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
