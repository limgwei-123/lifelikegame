import { apiRequest } from "./client.js";

export function createTaskSchedule(taskId, payload) {
  return apiRequest(`/tasks/${taskId}/task_schedules`, {
    method: "POST",
    body: payload
  });
}

export function listTaskSchedulesByTask(taskId) {
  return apiRequest(`/tasks/${taskId}/task_schedules`);
}

export function listTaskSchedules() {
  return apiRequest("/task_schedules");
}

export function getTaskSchedule(taskScheduleId) {
  return apiRequest(`/task_schedules/${taskScheduleId}`);
}

export function updateTaskSchedule(taskScheduleId, payload) {
  return apiRequest(`/task_schedules/${taskScheduleId}`, {
    method: "POST",
    body: payload
  });
}

export function deleteTaskSchedule(taskScheduleId) {
  return apiRequest(`/task_schedules/${taskScheduleId}/delete`, {
    method: "POST"
  });
}
