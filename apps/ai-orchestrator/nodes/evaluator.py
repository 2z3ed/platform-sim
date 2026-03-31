import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum

from providers.utils.fixture_loader import FixtureLoader


class ValidationError(BaseModel):
    field: str
    message: str
    severity: str = "error"


class ValidationResult(BaseModel):
    passed: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

    @property
    def error_count(self) -> int:
        return len([e for e in self.errors if e.severity == "error"])

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class Evaluator:
    def __init__(self):
        self.rules = [
            self._check_order_exists,
            self._check_refund_consistency,
            self._check_internal_fields,
            self._check_message_length,
            self._check_intent_emotion_consistency,
        ]

    def validate(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> ValidationResult:
        errors = []
        warnings = []

        for rule in self.rules:
            result = rule(message, decision, tool_results, platform)
            if result:
                if result.severity == "error":
                    errors.append(result)
                else:
                    warnings.append(result)

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_order_exists(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> Optional[ValidationError]:
        order_id = decision.get("selected_order_id")
        if not order_id:
            return None

        found = False
        for uid in FixtureLoader.list_users(platform):
            try:
                order = FixtureLoader.get_user_order(platform, uid, order_id)
                if order:
                    found = True
                    break
            except FileNotFoundError:
                continue

        if not found:
            return ValidationError(
                field="selected_order_id",
                message=f"引用了不存在的订单: {order_id}",
                severity="error",
            )
        return None

    def _check_refund_consistency(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> Optional[ValidationError]:
        intent = decision.get("intent", "")

        if intent not in ["ask_refund", "complain"]:
            return None

        order_id = decision.get("selected_order_id")
        if not order_id:
            return None

        has_refund = False
        for uid in FixtureLoader.list_users(platform):
            try:
                order = FixtureLoader.get_user_order(platform, uid, order_id)
                if order and order.get("refund"):
                    has_refund = True
                    break
            except FileNotFoundError:
                continue

        if not has_refund:
            return ValidationError(
                field="intent",
                message=f"用户说要退款但订单 {order_id} 没有退款记录",
                severity="error",
            )
        return None

    def _check_internal_fields(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> Optional[ValidationError]:
        internal_fields = [
            "advance_order_state",
            "emit_platform_push",
            "write_artifact",
            "sync_to_unified",
        ]

        combined = f"{message} {str(decision)} {str(tool_results)}"

        for field in internal_fields:
            if field.lower() in combined.lower():
                return ValidationError(
                    field="message",
                    message=f"消息中包含了系统内部字段: {field}",
                    severity="error",
                )
        return None

    def _check_message_length(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> Optional[ValidationError]:
        if len(message) > 200:
            return ValidationError(
                field="message",
                message=f"消息过长 ({len(message)}字符)，应控制在200字以内",
                severity="warning",
            )
        return None

    def _check_intent_emotion_consistency(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> Optional[ValidationError]:
        intent = decision.get("intent", "")
        emotion = decision.get("emotion", "")

        if emotion == "angry" and intent not in ["complain", "escalate_to_human"]:
            return ValidationError(
                field="emotion",
                message="情绪是angry但意图不是complain或escalate_to_human",
                severity="warning",
            )

        if emotion == "calm" and intent == "complain":
            return ValidationError(
                field="emotion",
                message="意图是complain但情绪是calm，可能不一致",
                severity="warning",
            )
        return None

    def validate_and_raise(
        self,
        message: str,
        decision: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        platform: str,
    ) -> None:
        result = self.validate(message, decision, tool_results, platform)
        if not result.passed:
            error_msgs = [f"{e.field}: {e.message}" for e in result.errors]
            raise ValueError(f"消息校验失败: {'; '.join(error_msgs)}")
