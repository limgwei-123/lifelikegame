from app.goals.schemas import CreateGoalRequest
from app.shared.enums import ScheduleType
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO

from app.tasks.dtos import CreateTaskDTO
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.ai_planner.schemas import GeneratedPlan, GeneratedTask
from datetime import date

def map_plan_to_goal_request(plan: GeneratedPlan) -> CreateGoalRequest:
    return CreateGoalRequest(
        title=plan.goal_title,
        start_date=date.today()
    )

def map_generated_task_to_task_with_schedule_request(
    ai_task: GeneratedTask,
) -> CreateTaskWithScheduleDTO:
    return CreateTaskWithScheduleDTO(
        task=CreateTaskDTO(
            title=ai_task.title,
            description=ai_task.description,
            is_active=True,
        ),
        schedule=CreateTaskScheduleDTO(
            schedule_type=ScheduleType(ai_task.schedule_type),
            schedule_value_json=ai_task.schedule_value_json,
            start_date=date.today()
        ),
    )


def map_plan_to_task_with_schedule_requests(
    plan: GeneratedPlan,
) -> list[CreateTaskWithScheduleDTO]:
    return [
        map_generated_task_to_task_with_schedule_request(ai_task)
        for ai_task in plan.tasks
    ]
