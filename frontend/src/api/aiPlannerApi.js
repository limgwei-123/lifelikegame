import { apiRequest } from "./client.js";

export function generateAiPlan(payload) {
  return apiRequest("/ai-planner/generate-plan", {
    method: "POST",
    body: payload
  });
}

export function saveAiDraftRevision(draftId, plan) {
  return apiRequest(`/ai-planner/drafts/${encodeURIComponent(draftId)}/revisions`, {
    method: "POST",
    body: plan
  });
}
