from langgraph.graph import StateGraph, END
from functools import partial

from app.ai_planner.providers.base import AIPlannerProvider
from app.ai_planner.state import AiPlannerGraphState
from app.ai_planner.nodes import (
    generate_ai_response_node,
    build_response_node,
)

def route_by_status(state: AiPlannerGraphState) -> str:
    status = state.get("status")

    return status



def build_ai_planner_graph(provider: AIPlannerProvider):
    graph = StateGraph(AiPlannerGraphState)

    graph.add_node("generate_ai_response", partial(generate_ai_response_node, provider=provider))
    graph.add_node("build_response", build_response_node)

    graph.set_entry_point("generate_ai_response")

    graph.add_conditional_edges(
      "generate_ai_response",
      route_by_status,
      {
        "need_more_info": "build_response",
        "plan_ready": "build_response",
        "build_response":"build_response"
      }
    )

    graph.add_edge("build_response", END)

    return graph.compile()
