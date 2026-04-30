import { apiRequest } from "./client.js";

export function createTask(goalId, payload) {
  return apiRequest(`/goals/${goalId}/tasks`, {
    method: "POST",
    body: payload
  });
}

export function listTasksByGoal(goalId) {
  return apiRequest(`/goals/${goalId}/tasks`);
}

export function listTasks() {
  return apiRequest("/tasks");
}

export function getTask(taskId) {
  return apiRequest(`/tasks/${taskId}`);
}

export function updateTask(taskId, payload) {
  return apiRequest(`/tasks/${taskId}`, {
    method: "POST",
    body: payload
  });
}

export function deleteTask(taskId) {
  return apiRequest(`/tasks/${taskId}/delete`, {
    method: "POST"
  });
}
