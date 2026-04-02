from typing import Dict, Any, List, Optional
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from providers.utils.fixture_loader import FixtureLoader


class WecomConversationStatus(str, Enum):
    PENDING = "pending"
    IN_SESSION = "in_session"
    CLOSED = "closed"
    EXPIRED = "expired"


class WecomMessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"
    MINIPROGRAM = "miniprogram"


WECOM_CONVERSATION_TRANSITIONS: Dict[WecomConversationStatus, List[WecomConversationStatus]] = {
    WecomConversationStatus.PENDING: [WecomConversationStatus.IN_SESSION],
    WecomConversationStatus.IN_SESSION: [WecomConversationStatus.CLOSED, WecomConversationStatus.EXPIRED],
    WecomConversationStatus.CLOSED: [],
    WecomConversationStatus.EXPIRED: [],
}


CONVERSATION_SCENARIOS = {
    "basic_session": {
        "initial_status": WecomConversationStatus.PENDING,
        "steps": [
            {"action": "start_session", "next_status": WecomConversationStatus.IN_SESSION},
        ],
    },
    "full_session": {
        "initial_status": WecomConversationStatus.PENDING,
        "steps": [
            {"action": "start_session", "next_status": WecomConversationStatus.IN_SESSION},
            {"action": "close_session", "next_status": WecomConversationStatus.CLOSED},
        ],
    },
    "session_expired": {
        "initial_status": WecomConversationStatus.IN_SESSION,
        "steps": [
            {"action": "expire_session", "next_status": WecomConversationStatus.EXPIRED},
        ],
    },
}


STATUS_TO_SCENARIO = {
    WecomConversationStatus.PENDING: "conversation_pending",
    WecomConversationStatus.IN_SESSION: "conversation_in_session",
    WecomConversationStatus.CLOSED: "conversation_closed",
    WecomConversationStatus.EXPIRED: "conversation_closed",
}


def get_default_callback_payload(open_id: str, code: str) -> Dict[str, Any]:
    return {
        "msg_type": "event",
        "event": "enter_session",
        "open_id": open_id,
        "scene": "wework",
        "session_from": "customer_service",
        "code": code,
        "token": "wecom_callback_token_12345",
        "timestamp": "1743235200",
    }


def get_default_sync_msg_payload(open_id: str, limit: int = 100) -> Dict[str, Any]:
    fixture = FixtureLoader.get_response("wecom_kf", "conversation_in_session")
    response = fixture.get("response", {})
    return {
        "errcode": 0,
        "errmsg": "ok",
        "msg_list": response.get("msg_list", []),
        "continue_token": "continue_token_abc123",
        "has_more": 0,
    }


def get_default_send_msg_payload(open_id: str, content: str) -> Dict[str, Any]:
    return {
        "errcode": 0,
        "errmsg": "ok",
        "msgid": f"MSG_{open_id}_001",
        "msgsrv": "https://qyapi.weixin.qq.com/cgi-bin/msga msg/send",
    }


def get_default_event_message_payload(
    open_id: str,
    event_type: str,
    agent_id: str = "1000001",
) -> Dict[str, Any]:
    event_templates = {
        "enter_session": {
            "event": "enter_session",
            "openid": open_id,
            "scene": "wework",
            "session_from": "customer_service",
            "create_time": "1743235200",
        },
        "session_close": {
            "event": "session_close",
            "openid": open_id,
            "close_type": "close_by_customer",
            "create_time": "1743235300",
        },
        "kf_msg": {
            "event": "kf_msg",
            "openid": open_id,
            "agentid": agent_id,
            "msgid": f"MSG_{open_id}_EVT",
            "msgtype": WecomMessageType.TEXT.value,
            "content": "客服消息内容",
            "create_time": "1743235300",
        },
    }
    return event_templates.get(event_type, {"event": event_type, "openid": open_id})


def validate_conversation_transition(
    current: WecomConversationStatus,
    next_status: WecomConversationStatus,
) -> bool:
    allowed = WECOM_CONVERSATION_TRANSITIONS.get(current, [])
    return next_status in allowed


def generate_wecom_sign(token: str, timestamp: str, nonce: str, encrypt: str = "") -> str:
    import hashlib
    sign_list = sorted([token, timestamp, nonce, encrypt])
    sign_str = "".join(sign_list)
    return hashlib.sha1(sign_str.encode()).hexdigest()


def verify_wecom_sign(
    token: str,
    timestamp: str,
    nonce: str,
    signature: str,
    encrypt: str = "",
) -> bool:
    expected = generate_wecom_sign(token, timestamp, nonce, encrypt)
    return signature == expected