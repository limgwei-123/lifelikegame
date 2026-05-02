from app.goals.schemas import CreateGoalRequest
from app.workflows.task_workflow.schemas import CreateTaskWithScheduleRequest,ConfirmAiPlanRequest

from app.tasks.schemas import CreateTaskRequest
from app.task_schedules.schemas import CreateTaskScheduleRequest
from app.ai_planner.schemas import GeneratedTask

def map_plan_to_goal_request(plan: ConfirmAiPlanRequest) -> CreateGoalRequest:
    return CreateGoalRequest(
        title=plan.goal_title
    )

def map_generated_task_to_task_with_schedule_request(
    ai_task: GeneratedTask,
) -> CreateTaskWithScheduleRequest:
    return CreateTaskWithScheduleRequest(
        task=CreateTaskRequest(
            title=ai_task.title,
            description=ai_task.description,
            is_active=True,
        ),
        schedule=CreateTaskScheduleRequest(
            schedule_type=ai_task.schedule_type,
            schedule_value_json=ai_task.schedule_value_json,
        ),
    )


def map_plan_to_task_with_schedule_requests(
    plan: ConfirmAiPlanRequest,
) -> list[CreateTaskWithScheduleRequest]:
    return [
        map_generated_task_to_task_with_schedule_request(ai_task)
        for ai_task in plan.tasks
    ]
