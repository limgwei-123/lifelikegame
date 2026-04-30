import { apiRequest } from "./client.js";

export function getMe() {
  return apiRequest("/users/me");
}

export function getUser(userId) {
  return apiRequest(`/users/${userId}`);
}
