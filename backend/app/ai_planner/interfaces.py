from abc import ABC, abstractmethod
from app.ai_planner.schemas import GeneratedPlan, AiPlannerResponse


class AIPlannerServiceInterface(ABC):

    @abstractmethod
    def generate_plan(self, payload: GeneratedPlan) -> AiPlannerResponse:
        pass