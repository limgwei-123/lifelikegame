from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse
from app.ai_planner.graph import build_ai_planner_graph
from app.ai_planner.providers.base import AIPlannerProvider


class AIPlannerService:
    def __init__(self, provider: AIPlannerProvider):
        self.graph = build_ai_planner_graph(provider)

    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        result = self.graph.invoke({
            "payload": payload,
        })

        return result["ai_response"]
