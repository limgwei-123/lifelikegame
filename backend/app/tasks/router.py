from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.tasks.schemas import (
  CreateTaskRequest,
  UpdateTaskRequest,
  TaskResponse
)

from app.task_workflows.schemas import TaskWithScheduleResponse

from app.tasks.interfaces import TaskServiceInterface
from app.tasks.dependencies import get_task_service
from app.task_workflows.dependencies import get_task_workflow_service
from app.task_workflows.interfaces import TaskWorkflowServiceInterface

router = APIRouter(tags=["tasks"])

@router.post('/goals/{goal_id}/tasks', response_model= TaskWithScheduleResponse, status_code= status.HTTP_201_CREATED)
def create_task(goal_id,
                payload: CreateTaskRequest,
                current_user = Depends(get_current_user),
                task_workflow_service: TaskWorkflowServiceInterface = Depends(get_task_workflow_service)):
  return task_workflow_service.create_task_with_schedule(
    goal_id = goal_id,
    user_id = current_user.id,
    payload = payload
  )

@router.get('/goals/{goal_id}/tasks', response_model=list[TaskResponse], status_code = status.HTTP_200_OK)
def list_tasks_by_goal_id(goal_id, current_user = Depends(get_current_user), task_service: TaskServiceInterface = Depends(get_task_service)):
  return task_service.list_tasks_by_goal_id(goal_id = goal_id, user_id = current_user.id)

@router.get('/tasks', response_model=list[TaskResponse], status_code= status.HTTP_200_OK)
def list_tasks_by_user_id(current_user = Depends(get_current_user), task_service: TaskServiceInterface = Depends(get_task_service)):
  return task_service.list_tasks_by_user_id(user_id= current_user.id)

@router.get('/tasks/{task_id}', response_model= TaskResponse, status_code= status.HTTP_200_OK)
def get_task_by_id(task_id,
                   current_user = Depends(get_current_user),
                   task_service: TaskServiceInterface = Depends(get_task_service)):
  return task_service.get_task_by_id(task_id= task_id, user_id= current_user.id)

@router.post('/tasks/{task_id}', response_model= TaskResponse, status_code= status.HTTP_200_OK)
def update_task(task_id,
                payload: UpdateTaskRequest,
                current_user = Depends(get_current_user),
                task_service: TaskServiceInterface = Depends(get_task_service)):
  return task_service.update_task(
    task_id= task_id,
    user_id= current_user.id,
    data= payload
  )

@router.post("/tasks/{task_id}/delete", status_code = status.HTTP_204_NO_CONTENT)
def delete_task(
  task_id,
  current_user = Depends(get_current_user),
  task_service: TaskServiceInterface = Depends(get_task_service)
):
  task_service.delete_task(task_id=task_id, user_id=current_user.id)