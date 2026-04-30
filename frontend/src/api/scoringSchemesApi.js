import { apiRequest } from "./client.js";

export function createScoringScheme(payload) {
  return apiRequest("/scoring_schemes", {
    method: "POST",
    body: payload
  });
}

export function listScoringSchemes() {
  return apiRequest("/scoring_schemes");
}

export function getScoringScheme(scoringSchemeId) {
  return apiRequest(`/scoring_schemes/${scoringSchemeId}`);
}

export function updateScoringScheme(scoringSchemeId, payload) {
  return apiRequest(`/scoring_schemes/${scoringSchemeId}`, {
    method: "POST",
    body: payload
  });
}

export function deleteScoringScheme(scoringSchemeId) {
  return apiRequest(`/scoring_schemes/${scoringSchemeId}/delete`, {
    method: "POST"
  });
}
