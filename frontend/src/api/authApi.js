import { apiRequest } from "./client.js";

export function signup(payload) {
  return apiRequest("/auth/signup", {
    method: "POST",
    body: payload
  });
}

export function login(payload) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: payload
  });
}
