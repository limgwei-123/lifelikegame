from langgraph.graph import StateGraph, END

from app.ai_planner.state import AiPlannerGraphState
from app.ai_planner.nodes import (
    generate_ai_response_node,
    normalize_schedule_node,
    build_response_node,
)

def route_by_status(state: AiPlannerGraphState) -> str:
    status = state.get("status")

    return status



def build_ai_planner_graph():
    graph = StateGraph(AiPlannerGraphState)

    graph.add_node("generate_ai_response", generate_ai_response_node)
    graph.add_node("normalize_schedule", normalize_schedule_node)
    graph.add_node("build_response", build_response_node)

    graph.set_entry_point("generate_ai_response")

    graph.add_conditional_edges(
      "generate_ai_response",
      route_by_status,
      {
        "need_more_info": "build_response",
        "plan_ready": "normalize_schedule",
        "build_response":"build_response"
      }
    )

    graph.add_edge("normalize_schedule", "build_response")
    graph.add_edge("build_response", END)

    return graph.compile()