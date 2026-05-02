from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.goals.interfaces import GoalServiceInterface
from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface

from app.workflows.task_workflow.schemas import CreateTaskWithScheduleRequest, TaskWithScheduleResponse,ConfirmAiPlanRequest,GoalTaskSchduleResponse

from app.shared.function import get_scoring_scheme_workflow
from app.workflows.task_workflow.mappers import map_plan_to_goal_request,map_plan_to_task_with_schedule_requests

class TaskWorkflowService:
  def __init__(self,
               goal_service: GoalServiceInterface,
               task_service: TaskServiceInterface,
               task_schedule_service: TaskScheduleServiceInterface,
               task_instance_service: TaskInstanceServiceInterface,
               scoring_scheme_service: ScoringSchemeServiceInterface):
    self.goal_service = goal_service
    self.task_service = task_service
    self.task_schedule_service = task_schedule_service
    self.task_instance_service = task_instance_service
    self.scoring_scheme_service = scoring_scheme_service

  def create_task_with_schedule(self, goal_id, user_id, payload: CreateTaskWithScheduleRequest):

    scoring_scheme = get_scoring_scheme_workflow(scoring_scheme_id=payload.task.scoring_scheme_id,scoring_scheme_service=self.scoring_scheme_service)

    payload.task.scoring_scheme_id = scoring_scheme.id
    payload.task.scoring_scheme_json = scoring_scheme.levels_json

    task = self.task_service.create_task(
      goal_id=goal_id,
      user_id=user_id,
      payload=payload.task,
      )

    schedule = None
    task_instance = None
    if payload.schedule:
      schedule = self.task_schedule_service.create_task_schedule(
        task_id= task.id,
        user_id=user_id,
        payload=payload.schedule
      )

      if payload.schedule.schedule_type == "once":
        task_instance = self.task_instance_service.create_task_instance_for_date(
          task_id=task.id,
          task_schedule_id=schedule.id,
          user_id = user_id,
          date_instance=schedule.start_date
        )

      task.schedule = schedule

    return TaskWithScheduleResponse(
      task=task,
      schedule=schedule,
      task_instance=task_instance
    )

  def create_from_ai_plan(self, user_id, payload:ConfirmAiPlanRequest)->GoalTaskSchduleResponse:


    goal_request = map_plan_to_goal_request(payload.plan)

    goal = self.goal_service.create_goal(user_id=user_id, payload=goal_request)

    task_with_schedule_requests = map_plan_to_task_with_schedule_requests(payload.plan)

    task_with_schedule_list=[]

    for task_payload in task_with_schedule_requests:
      task_schedule = self.create_task_with_schedule(
          goal_id=goal.id,
          user_id=user_id,
          payload=task_payload,
      )

      task_with_schedule_list.append(task_schedule)

    return GoalTaskSchduleResponse(
      goal=goal,
      task_with_schedule_list=task_with_schedule_list
    )