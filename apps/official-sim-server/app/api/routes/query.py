from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from providers.utils.fixture_loader import FixtureLoader

router = APIRouter()


class OrderSummary(BaseModel):
    order_id: str
    platform: str
    status: str
    status_text: str
    amount: str
    items: List[Dict[str, Any]]
    receiver: Dict[str, Any]
    created_at: Optional[str]
    paid_at: Optional[str]


class ShipmentSummary(BaseModel):
    order_id: str
    status: str
    company: Optional[str]
    tracking_no: Optional[str]
    nodes: List[Dict[str, str]]


class RefundSummary(BaseModel):
    order_id: str
    status: str
    amount: str
    reason: Optional[str]
    apply_time: Optional[str]
    refund_time: Optional[str]


class UserInfo(BaseModel):
    user_id: str
    platform: str
    name: str
    phone: str


class OrderQueryResponse(BaseModel):
    code: str = "0"
    message: str = "success"
    data: Dict[str, Any]


class UserOrdersResponse(BaseModel):
    code: str = "0"
    message: str = "success"
    data: Dict[str, Any]


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
    order_data = FixtureLoader.get_user_order(platform, order_id, order_id)
    if order_data:
        user_data = FixtureLoader.get_user_by_order(platform, order_id)
        return OrderQueryResponse(
            data={
                "order": order_data,
                "user": {
                    "user_id": user_data.get("user_id") if user_data else None,
                    "name": user_data.get("name") if user_data else None,
                }
            }
        )

    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                user_data = FixtureLoader.load_user(platform, uid)
                return OrderQueryResponse(
                    data={
                        "order": order_data,
                        "user": {
                            "user_id": user_data.get("user_id"),
                            "name": user_data.get("name"),
                        }
                    }
                )
        except FileNotFoundError:
            continue

    raise HTTPException(status_code=404, detail=f"Order {order_id} not found")


@router.get("/orders/{order_id}/shipment")
async def get_shipment(
    platform: str = Query(...),
    order_id: str = None
):
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                shipment = order_data.get("shipment")
                if not shipment:
                    raise HTTPException(status_code=404, detail=f"Shipment not found for order {order_id}")
                return OrderQueryResponse(
                    data={
                        "shipment": shipment,
                        "order_id": order_id
                    }
                )
        except FileNotFoundError:
            continue

    raise HTTPException(status_code=404, detail=f"Order {order_id} not found")


@router.get("/orders/{order_id}/refund")
async def get_refund(
    platform: str = Query(...),
    order_id: str = None
):
    for uid in FixtureLoader.list_users(platform):
        try:
            order_data = FixtureLoader.get_user_order(platform, uid, order_id)
            if order_data:
                refund = order_data.get("refund")
                if not refund:
                    raise HTTPException(status_code=404, detail=f"Refund not found for order {order_id}")
                return OrderQueryResponse(
                    data={
                        "refund": refund,
                        "order_id": order_id
                    }
                )
        except FileNotFoundError:
            continue

    raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
