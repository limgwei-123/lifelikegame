import { apiRequest } from "./client.js";

export function listTaskInstancesByDate(date) {
  return apiRequest(`/task_instances?date=${encodeURIComponent(date)}`);
}

export function listTaskInstancesByMonth(year, month) {
  return apiRequest(`/task_instances/month?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`);
}

export function createTaskInstanceForDate(taskId, taskScheduleId, payload) {
  return apiRequest(`/tasks/${taskId}/task_schedules/${taskScheduleId}/task_instances`, {
    method: "POST",
    body: payload
  });
}

export function generateTaskInstancesForDate(payload) {
  return apiRequest("/tasks_instances/generate", {
    method: "POST",
    body: payload
  });
}

export function completeTaskInstance(taskInstanceId, payload) {
  return apiRequest(`/task_instances/${taskInstanceId}/complete`, {
    method: "POST",
    body: payload
  });
}
