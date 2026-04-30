import { apiRequest } from "./client.js";

export function health() {
  return apiRequest("/health");
}

export function dbHealth() {
  return apiRequest("/db-health");
}
