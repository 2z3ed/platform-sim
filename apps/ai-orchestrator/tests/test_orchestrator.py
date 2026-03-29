import pytest
import sys
from pathlib import Path

sys.path.insert(0, '/home/kkk/Project/platform-sim/apps/ai-orchestrator')

from nodes.state import OrchestratorState, AgentStatus, OrderQuery, SuggestionRequest
from nodes.base import create_initial_state, start_node, error_node, end_node
from nodes.suggestion import get_suggestion_node, rule_check_node


def test_orchestrator_state_model():
    state = OrchestratorState()
    assert state.status == AgentStatus.IDLE
    assert state.suggestions == []
    assert state.errors == []


def test_order_query_model():
    query = OrderQuery(
        order_id="ORDER_001",
        platform="taobao",
        user_question="查询物流"
    )
    assert query.order_id == "ORDER_001"
    assert query.platform == "taobao"


def test_create_initial_state():
    state = create_initial_state()
    assert state.status == AgentStatus.IDLE
    assert state.current_order_id is None


def test_start_node():
    state = create_initial_state()
    state.current_order_id = "ORDER_001"
    state.current_platform = "taobao"
    result = start_node(state)
    assert result.status == AgentStatus.PROCESSING
    assert len(result.messages) == 1


def test_error_node():
    state = create_initial_state()
    result = error_node(state, "Test error")
    assert result.status == AgentStatus.FAILED
    assert "Test error" in result.errors


def test_end_node():
    state = create_initial_state()
    state.status = AgentStatus.PROCESSING
    result = end_node(state)
    assert result.status == AgentStatus.COMPLETED
    assert result.next_node == "end"


def test_suggestion_node():
    state = create_initial_state()
    state.current_platform = "taobao"
    state.unified_order = {"status": "wait_ship", "user_message": "什么时候发货"}
    result = get_suggestion_node(state)
    assert len(result.suggestions) > 0
    assert result.next_node == "rule_check"


def test_rule_check_node():
    state = create_initial_state()
    state.unified_order = {"status": "shipped", "user_message": "我想申请退款"}
    result = rule_check_node(state)
    assert result.selected_action == "refund_request"
    assert result.next_node == "end"


def test_suggestion_with_unknown_status():
    state = create_initial_state()
    state.current_platform = "unknown_platform"
    state.unified_order = {"status": "unknown", "user_message": "hello"}
    result = get_suggestion_node(state)
    assert len(result.suggestions) == 2
    assert "您好，请问有什么可以帮助您的？" in result.suggestions
