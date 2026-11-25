from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.goals.interfaces import GoalServiceInterface
from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface

from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO, TaskWithScheduleResultDTO
from app.workflows.task_workflow.schemas import TaskWithScheduleResponse,GoalTaskSchduleResponse
from app.ai_planner.draft_schemas import DraftPlan

from dataclasses import replace
from app.users.interfaces import UserServiceInterface
from app.shared.dates import player_today
from app.errors.exception import NotFoundError
from app.workflows.task_workflow.mappers import map_plan_to_goal_request,map_plan_to_task_with_schedule_requests

class TaskWorkflowService:
  def __init__(self,
               goal_service: GoalServiceInterface,
               task_service: TaskServiceInterface,
               task_schedule_service: TaskScheduleServiceInterface,
               task_instance_service: TaskInstanceServiceInterface,
               scoring_scheme_service: ScoringSchemeServiceInterface, user_service: UserServiceInterface):
    self.goal_service = goal_service
    self.task_service = task_service
    self.task_schedule_service = task_schedule_service
    self.task_instance_service = task_instance_service
    self.scoring_scheme_service = scoring_scheme_service
    self.user_service = user_service

  def _today(self, user_id):
    user = self.user_service.get_user_by_id(user_id)
    if user is None:
      raise NotFoundError('User not found')
    return player_today(user.timezone)

  def create_task_with_schedule(self, goal_id, user_id, payload: CreateTaskWithScheduleDTO):
    today = self._today(user_id) if payload.schedule else None
    return self._create_task_with_schedule(goal_id, user_id, payload, today)

  def _create_task_with_schedule(self, goal_id, user_id, payload, today):

    task = self.task_service.create_task(
      goal_id=goal_id,
      user_id=user_id,
      payload=payload.task,
      )

    schedule = None
    task_instance = None
    if payload.schedule:
      schedule_payload = payload.schedule
      if schedule_payload.start_date is None:
        schedule_payload = replace(schedule_payload, start_date=today)
      schedule = self.task_schedule_service.create_task_schedule(
        task_id= task.id,
        user_id=user_id,
        payload=schedule_payload
      )

      if payload.schedule.schedule_type == "once":
        task_instance = self.task_instance_service.create_task_instance_for_date(
          task_id=task.id,
          task_schedule_id=schedule.id,
          user_id = user_id,
          date_instance=schedule.start_date
        )

      generated = self.task_instance_service.generate_task_instances_for_user(today, user_id)
      if payload.schedule.schedule_type != 'once':
        task_instance = next((row for row in generated if row.task_id == task.id), None)

      task.schedule = schedule

    return TaskWithScheduleResultDTO(
      task=task,
      schedule=schedule,
      task_instance=task_instance
    )

  def create_from_ai_plan(self, user_id, plan:DraftPlan)->GoalTaskSchduleResponse:


    today = self._today(user_id)
    goal_request = map_plan_to_goal_request(plan, today)

    goal = self.goal_service.create_goal(user_id=user_id, payload=goal_request)

    task_with_schedule_requests = map_plan_to_task_with_schedule_requests(plan, today)

    task_with_schedule_list=[]

    for task_payload in task_with_schedule_requests:
      task_schedule_result = self._create_task_with_schedule(
          goal_id=goal.id,
          user_id=user_id,
          payload=task_payload,
          today=today,
      )

      task_with_schedule_list.append(TaskWithScheduleResponse.model_validate(
        task_schedule_result,
        from_attributes=True,
      ))

    self.task_instance_service.generate_task_instances_for_user(today, user_id)

    return GoalTaskSchduleResponse(
      goal=goal,
      task_with_schedule_list=task_with_schedule_list
    )
