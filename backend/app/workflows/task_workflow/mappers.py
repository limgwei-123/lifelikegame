from app.goals.schemas import CreateGoalRequest
from app.shared.enums import ScheduleType
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO

from app.tasks.dtos import CreateTaskDTO
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.ai_planner.draft_schemas import DraftPlan, DraftTask
from datetime import date

def map_plan_to_goal_request(plan: DraftPlan, start_date: date) -> CreateGoalRequest:
    return CreateGoalRequest(
        title=plan.goal_title,
        start_date=start_date
    )

def map_generated_task_to_task_with_schedule_request(
    ai_task: DraftTask,
    start_date: date,
) -> CreateTaskWithScheduleDTO:
    return CreateTaskWithScheduleDTO(
        task=CreateTaskDTO(
            title=ai_task.title,
            description=ai_task.description,
            is_active=True,
            scoring_scheme_id=ai_task.scoring_scheme_id,
        ),
        schedule=CreateTaskScheduleDTO(
            schedule_type=ScheduleType(ai_task.schedule_type),
            schedule_value_json=ai_task.schedule_value_json,
            start_date=start_date
        ),
    )


def map_plan_to_task_with_schedule_requests(
    plan: DraftPlan,
    start_date: date,
) -> list[CreateTaskWithScheduleDTO]:
    return [
        map_generated_task_to_task_with_schedule_request(ai_task, start_date)
        for ai_task in plan.tasks
    ]
