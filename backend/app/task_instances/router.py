from fastapi import APIRouter, Depends, status, Query

from app.auth.dependencies import get_current_user
from app.task_instances.schemas import TaskInstanceResponse, CompleteTaskInstanceRequest

from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.task_instances.dependencies import get_task_instance_service

from datetime import date

router = APIRouter(tags=["task_instances"])

@router.get("/task_instances", response_model=list[TaskInstanceResponse], status_code=status.HTTP_200_OK)
def list_task_instance_by_date(
  date_instance: date = Query(..., alias="date"),
  current_user = Depends(get_current_user),
  task_instance_service: TaskInstanceServiceInterface = Depends(get_task_instance_service)
):
  return task_instance_service.list_task_instances_by_date(user_id=current_user.id, date_instance= date_instance)

@router.post("/task_instances/{task_instance_id}/complete", response_model=TaskInstanceResponse, status_code=status.HTTP_200_OK)
def complete_task_instance(task_instance_id, payload: CompleteTaskInstanceRequest, current_user = Depends(get_current_user), task_instance_service:TaskInstanceServiceInterface = Depends(get_task_instance_service)):
  task_instance = task_instance_service.complete_task_instance(task_instance_id=task_instance_id, user_id= current_user.id, completion_level= payload.completion_level)
  return task_instance