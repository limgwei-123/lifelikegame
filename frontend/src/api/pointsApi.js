import { apiRequest } from "./client.js";

export function createPointLedger(payload) {
  return apiRequest("/point_ledgers", {
    method: "POST",
    body: payload
  });
}

export function listPointLedgers() {
  return apiRequest("/point_ledgers");
}

export function getPointsBalance() {
  return apiRequest("/point_ledgers/balance");
}
