from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.tasks.schemas import TaskResponse
from app.task_schedules.schemas import TaskScheduleResponse
from app.goals.schemas import GoalResponse



from pydantic import BaseModel

from app.tasks.schemas import CreateTaskRequest, TaskResponse
from app.task_schedules.schemas import CreateTaskScheduleRequest, TaskScheduleResponse

from app.task_instances.schemas import TaskInstanceResponse


class CreateTaskWithScheduleRequest(BaseModel):
    task: CreateTaskRequest
    schedule: CreateTaskScheduleRequest | None = None

class TaskWithScheduleResponse(BaseModel):
    task: TaskResponse
    schedule: TaskScheduleResponse | None = None
    task_instance: TaskInstanceResponse | None = None

class ConfirmAiPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: UUID

class GoalTaskSchduleResponse(BaseModel):
    goal:GoalResponse
    task_with_schedule_list: list[TaskWithScheduleResponse]
