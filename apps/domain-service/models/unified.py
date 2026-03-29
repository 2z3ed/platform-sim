from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Platform(str, Enum):
    TAOBAO = "taobao"
    DOUYIN_SHOP = "douyin_shop"
    WECOM_KF = "wecom_kf"
    JD = "jd"
    XHS = "xhs"
    KUAISHOU = "kuaishou"


class OrderStatus(str, Enum):
    WAIT_PAY = "wait_pay"
    PAID = "paid"
    WAIT_SHIP = "wait_ship"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    FINISHED = "finished"
    TRADE_CLOSED = "trade_closed"
    REFUNDING = "refunding"
    REFUNDED = "refunded"


class RefundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDING = "refunding"
    COMPLETED = "completed"


class ConversationStatus(str, Enum):
    PENDING = "pending"
    IN_SESSION = "in_session"
    CLOSED = "closed"


class UnifiedAddress(BaseModel):
    name: str
    phone: str = Field(description="Phone number, masked for privacy")
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: str


class UnifiedProduct(BaseModel):
    product_id: str
    name: str
    price: str = Field(description="Price as string to avoid floating point issues")
    quantity: int = 1


class UnifiedOrder(BaseModel):
    order_id: str
    platform: Platform
    status: OrderStatus
    total_amount: str
    pay_amount: str
    freight: str = "0.00"
    receiver: UnifiedAddress
    products: List[UnifiedProduct] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    external_order_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class UnifiedShipmentNode(BaseModel):
    node: str
    time: datetime
    description: Optional[str] = None


class UnifiedShipment(BaseModel):
    shipment_id: str
    order_id: str
    platform: Platform
    status: str
    company: Optional[str] = None
    tracking_no: Optional[str] = None
    nodes: List[UnifiedShipmentNode] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UnifiedRefund(BaseModel):
    refund_id: str
    order_id: str
    platform: Platform
    status: RefundStatus
    reason: str
    description: Optional[str] = None
    refund_amount: str
    created_at: datetime
    updated_at: datetime


class UnifiedMessage(BaseModel):
    msg_id: str
    conversation_id: str
    platform: Platform
    msg_type: str
    content: str
    sender: str
    sender_type: str
    created_at: datetime


class UnifiedConversation(BaseModel):
    conversation_id: str
    platform: Platform
    status: ConversationStatus
    openid: Optional[str] = None
    scene: Optional[str] = None
    created_at: datetime
    updated_at: datetime
