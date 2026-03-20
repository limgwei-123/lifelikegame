from pydantic import BaseModel
from app.tasks.schemas import TaskResponse
from app.task_schedules.schemas import TaskScheduleResponse


class TaskWithScheduleResponse(BaseModel):
    task: TaskResponse
    schedule: TaskScheduleResponse | None = None