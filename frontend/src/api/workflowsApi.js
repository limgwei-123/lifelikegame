import { apiRequest } from "./client.js";

export function createTaskWithSchedule(goalId, payload) {
  return apiRequest(`/workflows/goals/${goalId}/tasks`, {
    method: "POST",
    body: payload
  });
}

export function redeemReward(rewardId) {
  return apiRequest(`/workflows/rewards/${rewardId}/redeem`, {
    method: "POST"
  });
}

export function confirmAiPlan(plan) {
  return apiRequest("/workflows/ai/confirm", {
    method: "POST",
    body: { plan }
  });
}
