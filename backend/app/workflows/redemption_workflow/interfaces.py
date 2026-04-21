from app.workflows.task_workflow.schemas import CreateTaskScheduleRequest, TaskScheduleResponse
from typing import Protocol

class RedemptionWorkflowServiceInterface(Protocol):

    def redemption_workflow(self,reward_id, user_id):
        ...
