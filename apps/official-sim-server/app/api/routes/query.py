from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from providers.utils.fixture_loader import FixtureLoader
from app.domain.state_machine import state_machine
from app.domain.error_injector import error_injector
from app.domain.event_log import event_log
from app.domain.order_facts import (
    NormalizedOrderFacts,
    normalize_fixture_order,
    normalize_odoo_order,
)
from app.domain.shipment_facts import (
    NormalizedShipmentFacts,
    normalize_fixture_shipment,
    normalize_odoo_shipment,
)
from app.domain.aftersale_facts import (
    NormalizedAfterSaleFacts,
    normalize_fixture_aftersale,
    normalize_odoo_aftersale,
)
from app.domain.odoo_order_fetcher import OdooOrderFetcher
from app.domain.odoo_shipment_fetcher import OdooShipmentFetcher
from app.domain.odoo_aftersale_fetcher import OdooAfterSaleFetcher
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class OrderQueryResponse(BaseModel):
    code: str = "0"
    message: str = "success"
    data: Dict[str, Any]


class UserOrdersResponse(BaseModel):
    code: str = "0"
    message: str = "success"
    data: Dict[str, Any]


# Lazy Odoo fetcher singleton
_odoo_fetcher = None


def _get_odoo_fetcher() -> Optional[OdooOrderFetcher]:
    global _odoo_fetcher
    if _odoo_fetcher is None:
        if not settings.odoo_api_key:
            return None
        try:
            _odoo_fetcher = OdooOrderFetcher(
                base_url=settings.odoo_base_url,
                db=settings.odoo_db,
                username=settings.odoo_username,
                api_key=settings.odoo_api_key,
                timeout=settings.odoo_timeout,
            )
        except Exception as e:
            logger.warning(f"Failed to create Odoo fetcher: {e}")
            return None
    return _odoo_fetcher


def _fetch_order_facts(platform: str, order_id: str) -> Optional[NormalizedOrderFacts]:
    """
    Fetch order facts from the configured source (odoo or fixture).
    Returns normalized facts or None if not found.
    """
    source_mode = settings.order_source_mode

    # Try Odoo first if configured
    if source_mode == "odoo":
        fetcher = _get_odoo_fetcher()
        if fetcher and fetcher.is_available():
            try:
                raw_order = fetcher.fetch_order(order_id)
                if raw_order:
                    facts = normalize_odoo_order(raw_order)
                    logger.info(f"Order {order_id} loaded from Odoo (source=odoo)")
                    return facts
            except Exception as e:
                logger.warning(f"Odoo fetch failed for {order_id}: {e}")

    # Fallback to fixture
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                facts = normalize_fixture_order(platform, order_data)
                logger.info(f"Order {order_id} loaded from fixture (source=fixture)")
                return facts
        except FileNotFoundError:
            continue

    return None


# Lazy Odoo shipment fetcher singleton
_odoo_shipment_fetcher = None


def _get_odoo_shipment_fetcher() -> Optional[OdooShipmentFetcher]:
    global _odoo_shipment_fetcher
    if _odoo_shipment_fetcher is None:
        if not settings.odoo_api_key:
            return None
        try:
            _odoo_shipment_fetcher = OdooShipmentFetcher(
                base_url=settings.odoo_base_url,
                db=settings.odoo_db,
                username=settings.odoo_username,
                api_key=settings.odoo_api_key,
                timeout=settings.odoo_timeout,
            )
        except Exception as e:
            logger.warning(f"Failed to create Odoo shipment fetcher: {e}")
            return None
    return _odoo_shipment_fetcher


def _fetch_shipment_facts(platform: str, order_id: str) -> Optional[NormalizedShipmentFacts]:
    """
    Fetch shipment facts from the configured source (odoo or fixture).
    Returns normalized facts or None if not found.
    """
    source_mode = settings.order_source_mode

    # Try Odoo first if configured
    if source_mode == "odoo":
        fetcher = _get_odoo_shipment_fetcher()
        if fetcher and fetcher.is_available():
            try:
                raw_shipment = fetcher.fetch_shipment_by_order(order_id)
                if raw_shipment:
                    facts = normalize_odoo_shipment(raw_shipment)
                    logger.info(f"Shipment for order {order_id} loaded from Odoo (source=odoo)")
                    return facts
            except Exception as e:
                logger.warning(f"Odoo shipment fetch failed for order {order_id}: {e}")

    # Fallback to fixture
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                shipment = order_data.get("shipment")
                if shipment:
                    facts = normalize_fixture_shipment(shipment, order_id)
                    logger.info(f"Shipment for order {order_id} loaded from fixture (source=fixture)")
                    return facts
        except FileNotFoundError:
            continue

    return None


def _transform_shipment_to_payload(platform: str, facts: NormalizedShipmentFacts) -> Dict[str, Any]:
    """Transform normalized shipment facts into platform-specific payload."""
    if platform == "taobao":
        from app.platforms.taobao.profile import transform_shipment_facts as tb_transform
        return tb_transform(facts)
    elif platform == "douyin_shop":
        from app.platforms.douyin_shop.profile import transform_shipment_facts as dy_transform
        return dy_transform(facts)
    elif platform == "jd":
        from app.platforms.jd.profile import transform_shipment_facts as jd_transform
        return jd_transform(facts)
    return {}


# Lazy Odoo aftersale fetcher singleton
_odoo_aftersale_fetcher = None


def _get_odoo_aftersale_fetcher() -> Optional[OdooAfterSaleFetcher]:
    global _odoo_aftersale_fetcher
    if _odoo_aftersale_fetcher is None:
        if not settings.odoo_api_key:
            return None
        try:
            _odoo_aftersale_fetcher = OdooAfterSaleFetcher(
                base_url=settings.odoo_base_url,
                db=settings.odoo_db,
                username=settings.odoo_username,
                api_key=settings.odoo_api_key,
                timeout=settings.odoo_timeout,
            )
        except Exception as e:
            logger.warning(f"Failed to create Odoo aftersale fetcher: {e}")
            return None
    return _odoo_aftersale_fetcher


def _fetch_aftersale_facts(platform: str, order_id: str) -> Optional[NormalizedAfterSaleFacts]:
    """
    Fetch after-sale facts from the configured source (odoo or fixture).
    Returns normalized facts or None if not found.
    """
    source_mode = settings.order_source_mode

    # Try Odoo first if configured
    if source_mode == "odoo":
        fetcher = _get_odoo_aftersale_fetcher()
        if fetcher and fetcher.is_available():
            try:
                raw_aftersale = fetcher.fetch_aftersale_by_order(order_id)
                if raw_aftersale:
                    facts = normalize_odoo_aftersale(raw_aftersale)
                    logger.info(f"After-sale for order {order_id} loaded from Odoo (source=odoo)")
                    return facts
            except Exception as e:
                logger.warning(f"Odoo aftersale fetch failed for order {order_id}: {e}")

    # Fallback to fixture
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                refund = order_data.get("refund")
                if refund:
                    facts = normalize_fixture_aftersale(refund, order_id)
                    logger.info(f"After-sale for order {order_id} loaded from fixture (source=fixture)")
                    return facts
        except FileNotFoundError:
            continue

    return None


def _transform_aftersale_to_payload(platform: str, facts: NormalizedAfterSaleFacts) -> Dict[str, Any]:
    """Transform normalized after-sale facts into platform-specific payload."""
    if platform == "taobao":
        from app.platforms.taobao.profile import transform_aftersale_facts as tb_transform
        return tb_transform(facts)
    elif platform == "douyin_shop":
        from app.platforms.douyin_shop.profile import transform_aftersale_facts as dy_transform
        return dy_transform(facts)
    elif platform == "jd":
        from app.platforms.jd.profile import transform_aftersale_facts as jd_transform
        return jd_transform(facts)
    return {}


def _extract_status_from_fixture(platform: str, resource_type: str, order_data: dict) -> str:
    """Extract current status from fixture payload for state machine initialization."""
    if resource_type == "order":
        return order_data.get("status", "unknown")
    elif resource_type == "shipment":
        shipment = order_data.get("shipment", {})
        return shipment.get("status", "unknown")
    elif resource_type == "after_sale":
        refund = order_data.get("refund", {})
        return refund.get("status", "unknown")
    return "unknown"


def _ensure_state_initialized(platform: str, resource_type: str, resource_id: str, order_data: dict):
    """Initialize state machine from fixture if not already initialized."""
    existing = state_machine.get_state(platform, resource_type, resource_id)
    if existing:
        return
    current_status = _extract_status_from_fixture(platform, resource_type, order_data)
    if current_status and current_status != "unknown":
        state_machine.init_state(platform, resource_type, resource_id, current_status)


def _apply_state_to_payload(platform: str, resource_type: str, resource_id: str, payload: dict) -> dict:
    """Override payload status fields with current state machine status."""
    state = state_machine.get_state(platform, resource_type, resource_id)
    if not state:
        return payload
    current_status = state.current_status
    if resource_type == "order":
        if platform == "taobao" and "trade" in payload:
            payload["trade"]["status"] = current_status
        else:
            payload["status"] = current_status
    elif resource_type == "shipment":
        payload["status"] = current_status
    elif resource_type == "after_sale":
        payload["status"] = current_status
    return payload


def _check_error_injection(platform: str, resource_type: str, resource_id: str):
    """Check if error should be injected. Returns error response dict or None."""
    injection = error_injector.check(platform, resource_type, resource_id)
    if not injection:
        return None
    error_type = injection.error_type
    error_messages = {
        400: {"error": "invalid_param", "message": "请求参数错误", "http_status": 400, "retryable": False},
        401: {"error": "auth_failed", "message": "认证失败", "http_status": 401, "retryable": True},
        403: {"error": "permission_denied", "message": "权限不足", "http_status": 403, "retryable": False},
        429: {"error": "rate_limited", "message": "请求过于频繁", "http_status": 429, "retryable": True},
        503: {"error": "service_unavailable", "message": "服务暂时不可用", "http_status": 503, "retryable": True},
    }
    return error_messages.get(error_type, {"error": "unknown", "message": "未知错误", "http_status": 500, "retryable": False})


@router.get("/users")
async def list_users(platform: str = Query(...)):
    user_ids = FixtureLoader.list_users(platform)
    users = []
    for uid in user_ids:
        try:
            user_data = FixtureLoader.load_user(platform, uid)
            users.append({
                "user_id": user_data.get("user_id"),
                "platform": user_data.get("platform"),
                "name": user_data.get("name"),
                "phone": user_data.get("phone"),
            })
        except FileNotFoundError:
            continue
    return OrderQueryResponse(
        data={
            "users": users,
            "total": len(users)
        }
    )


@router.get("/users/{user_id}")
async def get_user(platform: str = Query(...), user_id: str = None):
    try:
        user_data = FixtureLoader.load_user(platform, user_id)
        return OrderQueryResponse(
            data={
                "user": {
                    "user_id": user_data.get("user_id"),
                    "platform": user_data.get("platform"),
                    "name": user_data.get("name"),
                    "phone": user_data.get("phone"),
                    "created_at": user_data.get("created_at"),
                }
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@router.get("/users/{user_id}/orders")
async def get_user_orders(platform: str = Query(...), user_id: str = None):
    try:
        orders = FixtureLoader.get_user_orders(platform, user_id)
        return UserOrdersResponse(
            data={
                "orders": orders,
                "total": len(orders)
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@router.get("/orders/{order_id}")
async def get_order(
    platform: str = Query(...),
    order_id: str = None
):
    # Check error injection first
    error_resp = _check_error_injection(platform, "order", order_id)
    if error_resp:
        raise HTTPException(status_code=error_resp["http_status"], detail=error_resp)

    # Fetch normalized facts (odoo or fixture)
    facts = _fetch_order_facts(platform, order_id)
    if not facts:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    # Transform facts to platform payload
    from app.api.routes.state import _transform_facts_to_payload
    payload = _transform_facts_to_payload(platform, facts)

    # Initialize state machine from facts
    state_machine.init_state(platform, "order", order_id, facts.status)
    # Apply state machine status to payload
    payload = _apply_state_to_payload(platform, "order", order_id, payload)

    # Log source (not exposed in response)
    logger.info(f"Order query: {order_id} platform={platform} source={facts.source}")

    return OrderQueryResponse(
        data={
            "order": payload,
            "user": {
                "user_id": f"{platform}_user",
                "name": facts.receiver.name,
            }
        }
    )


@router.get("/orders/{order_id}/shipment")
async def get_shipment(
    platform: str = Query(...),
    order_id: str = None
):
    error_resp = _check_error_injection(platform, "shipment", order_id)
    if error_resp:
        raise HTTPException(status_code=error_resp["http_status"], detail=error_resp)

    # Fetch normalized shipment facts (odoo or fixture)
    facts = _fetch_shipment_facts(platform, order_id)
    if not facts:
        raise HTTPException(status_code=404, detail=f"Shipment not found for order {order_id}")

    # Transform facts to platform payload
    payload = _transform_shipment_to_payload(platform, facts)

    # Initialize state machine from facts
    state_machine.init_state(platform, "shipment", order_id, facts.status)
    # Apply state machine status to payload
    payload = _apply_state_to_payload(platform, "shipment", order_id, payload)

    # Log source (not exposed in response)
    logger.info(f"Shipment query: order={order_id} platform={platform} source={facts.source}")

    return OrderQueryResponse(
        data={
            "shipment": payload,
            "order_id": order_id
        }
    )


@router.get("/orders/{order_id}/refund")
async def get_refund(
    platform: str = Query(...),
    order_id: str = None
):
    error_resp = _check_error_injection(platform, "after_sale", order_id)
    if error_resp:
        raise HTTPException(status_code=error_resp["http_status"], detail=error_resp)

    # Fetch normalized after-sale facts (odoo or fixture)
    facts = _fetch_aftersale_facts(platform, order_id)
    if not facts:
        raise HTTPException(status_code=404, detail=f"Refund not found for order {order_id}")

    # Transform facts to platform payload
    payload = _transform_aftersale_to_payload(platform, facts)

    # Initialize state machine from facts
    state_machine.init_state(platform, "after_sale", order_id, facts.status)
    # Apply state machine status to payload
    payload = _apply_state_to_payload(platform, "after_sale", order_id, payload)

    # Log source (not exposed in response)
    logger.info(f"Refund query: order={order_id} platform={platform} source={facts.source}")

    return OrderQueryResponse(
        data={
            "refund": payload,
            "order_id": order_id
        }
    )
