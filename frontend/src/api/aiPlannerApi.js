import { apiRequest } from "./client.js";

export function generateAiPlan(payload) {
  return apiRequest("/ai-planner/generate-plan", {
    method: "POST",
    body: payload
  });
}
