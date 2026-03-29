from langgraph.graph import StateGraph, END
from typing import Dict, Any

from ..nodes.state import OrchestratorState
from ..nodes.base import create_initial_state, start_node, error_node, end_node
from ..nodes.suggestion import get_suggestion_node, rule_check_node


def build_orchestrator_graph() -> StateGraph:
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("start", start_node)
    workflow.add_node("suggestion", get_suggestion_node)
    workflow.add_node("rule_check", rule_check_node)
    workflow.add_node("error", error_node)
    workflow.add_node("end", end_node)

    workflow.set_entry_point("start")

    workflow.add_edge("start", "suggestion")
    workflow.add_edge("suggestion", "rule_check")
    workflow.add_edge("rule_check", "end")
    workflow.add_edge("end", END)
    workflow.add_edge("error", END)

    return workflow.compile()


def route_based_on_state(state: OrchestratorState) -> str:
    if state.errors:
        return "error"
    return "end"


class OrchestratorGraph:
    def __init__(self):
        self.graph = build_orchestrator_graph()

    def run(self, order_id: str, platform: str, unified_order: Dict[str, Any]) -> OrchestratorState:
        initial_state = create_initial_state()
        initial_state.current_order_id = order_id
        initial_state.current_platform = platform
        initial_state.unified_order = unified_order

        result = self.graph.invoke(initial_state)
        return result

    def get_graph(self):
        return self.graph
