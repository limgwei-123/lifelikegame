import { apiRequest } from "./client.js";

export function createReward(payload) {
  return apiRequest("/rewards", {
    method: "POST",
    body: payload
  });
}

export function listRewards() {
  return apiRequest("/rewards");
}

export function getReward(rewardId) {
  return apiRequest(`/rewards/${rewardId}`);
}

export function updateReward(rewardId, payload) {
  return apiRequest(`/rewards/${rewardId}`, {
    method: "POST",
    body: payload
  });
}

export function deleteReward(rewardId) {
  return apiRequest(`/rewards/${rewardId}/delete`, {
    method: "POST"
  });
}
