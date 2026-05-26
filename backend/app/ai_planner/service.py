from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse
from app.ai_planner.graph import build_ai_planner_graph


class AIPlannerService:
    def __init__(self):
        self.graph = build_ai_planner_graph()

    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        result = self.graph.invoke({
            "payload": payload,
        })

        return result["ai_response"]