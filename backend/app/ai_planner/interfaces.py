from abc import ABC, abstractmethod
from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse


class AIPlannerServiceInterface(ABC):

    @abstractmethod
    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        pass