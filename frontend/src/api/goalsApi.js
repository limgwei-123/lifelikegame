import { apiRequest } from "./client.js";

export function createGoal(payload) {
  return apiRequest("/goals", {
    method: "POST",
    body: payload
  });
}

export function listGoals() {
  return apiRequest("/goals");
}

export function getGoal(goalId) {
  return apiRequest(`/goals/${goalId}`);
}

export function updateGoal(goalId, payload) {
  return apiRequest(`/goals/${goalId}`, {
    method: "POST",
    body: payload
  });
}

export function deleteGoal(goalId) {
  return apiRequest(`/goals/${goalId}/delete`, {
    method: "POST"
  });
}
