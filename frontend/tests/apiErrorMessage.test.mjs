import assert from "node:assert/strict";
import test from "node:test";

test("API errors surface stable domain messages and validation details", async () => {
  const { apiErrorMessage } = await import("../src/api/errorMessage.mjs");
  assert.equal(apiErrorMessage({ message: "This AI draft has already been confirmed" }), "This AI draft has already been confirmed");
  assert.equal(apiErrorMessage({ detail: "Not authenticated" }), "Not authenticated");
  assert.equal(apiErrorMessage({ detail: [{ loc: ["body", "tasks"], msg: "Too many tasks" }] }), "tasks: Too many tasks");
  assert.equal(apiErrorMessage("Gateway unavailable"), "Gateway unavailable");
  assert.equal(apiErrorMessage(null), "API request failed");
});
