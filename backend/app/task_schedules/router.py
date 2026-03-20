from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.task_schedules.schemas import CreateTaskScheduleRequest, UpdateTaskScheduleRequest, TaskScheduleResponse
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.task_schedules.dependencies import get_task_schedule_service

router = APIRouter(tags=["task_schedules"])

@router.post('/tasks/{task_id}/task_schedules', response_model= TaskScheduleResponse, status_code= status.HTTP_201_CREATED)
def create_task(task_id,
                payload: CreateTaskScheduleRequest,
                current_user = Depends(get_current_user),
                task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)):
  return task_schedule_service.create_task_schedule(
    task_id = task_id,
    user_id = current_user.id,
    payload = payload
  )

@router.get('/tasks/{task_id}/task_schedules', response_model=list[TaskScheduleResponse], status_code = status.HTTP_200_OK)
def list_task_schedules_by_task_id(task_id, current_user = Depends(get_current_user), task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)):
  return task_schedule_service.list_task_schedules_by_task_id(task_id = task_id, user_id = current_user.id)

@router.get('/task_schedules', response_model=list[TaskScheduleResponse], status_code= status.HTTP_200_OK)
def list_task_schedules_by_user_id(current_user = Depends(get_current_user), task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)):
  return task_schedule_service.list_task_schedules_by_user_id(user_id= current_user.id)

@router.get('/task_schedules/{task_schedule_id}', response_model= TaskScheduleResponse, status_code= status.HTTP_200_OK)
def get_task_by_id(task_schedule_id,
                   current_user = Depends(get_current_user),
                   task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)):
  return task_schedule_service.get_task_schedule_by_id(task_schedule_id= task_schedule_id, user_id= current_user.id)

@router.post('/task_schedules/{task_schedule_id}', response_model= TaskScheduleResponse, status_code= status.HTTP_200_OK)
def update_task(task_schedule_id,
                payload: UpdateTaskScheduleRequest,
                current_user = Depends(get_current_user),
                task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)):
  return task_schedule_service.update_task_schedule(
    task_schedule_id= task_schedule_id,
    user_id= current_user.id,
    data= payload
  )

@router.post("/task_schedules/{task_schedule_id}/delete", status_code = status.HTTP_204_NO_CONTENT)
def delete_task(
  task_schedule_id,
  current_user = Depends(get_current_user),
  task_schedule_service: TaskScheduleServiceInterface = Depends(get_task_schedule_service)
):
  task_schedule_service.delete_task_schedule(task_schedule_id=task_schedule_id, user_id=current_user.id)