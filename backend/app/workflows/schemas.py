from pydantic import BaseModel
from app.tasks.schemas import TaskResponse
from app.task_schedules.schemas import TaskScheduleResponse



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