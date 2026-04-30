import { apiRequest } from "./client.js";

export function createRedemption(payload) {
  return apiRequest("/redemptions", {
    method: "POST",
    body: payload
  });
}

export function listRedemptions() {
  return apiRequest("/redemptions");
}

export function getRedemption(redemptionId) {
  return apiRequest(`/redemptions/${redemptionId}`);
}
