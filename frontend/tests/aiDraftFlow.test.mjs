import assert from "node:assert/strict";
import test from "node:test";

const plan = { goal_title: "Fitness", tasks: [{ title: "Walk", schedule_type: "daily", schedule_value_json: {} }] };
const edited = { ...plan, goal_title: "Edited" };
const draft = { draft_id: "original", plan };

async function flow(options) {
  const { createAiDraftFlow } = await import("../src/pages/aiDraftFlow.mjs");
  const result = createAiDraftFlow(options);
  result.setDraft(draft);
  return result;
}

test("edits are saved before confirming only the canonical revision ID", async () => {
  const calls = [];
  const f = await flow({
    saveRevision: async (id, payload) => { calls.push(["save", id, payload]); return { draft_id: "revised", plan: edited }; },
    confirmDraft: async (id) => { calls.push(["confirm", id]); return "created"; }
  });
  f.markEdited(edited);
  assert.equal(await f.confirm(), "created");
  assert.deepEqual(calls, [["save", "original", edited], ["confirm", "revised"]]);
  await assert.rejects(f.confirm(), /draft/i);
});

test("failed confirmation retries the saved ID without another revision", async () => {
  let saves = 0;
  let confirms = 0;
  const ids = [];
  const f = await flow({
    saveRevision: async () => { saves++; return { draft_id: "revised", plan: { ...edited, canonical: true } }; },
    confirmDraft: async (id) => { ids.push(id); if (++confirms === 1) throw Error("temporary"); }
  });
  f.markEdited(edited);
  await assert.rejects(f.confirm(), /temporary/);
  f.markEdited(edited);
  await f.confirm();
  assert.equal(saves, 1);
  assert.deepEqual(ids, ["revised", "revised"]);
});

test("editing after failed confirmation saves a new revision", async () => {
  const sources = [];
  let confirms = 0;
  const f = await flow({
    saveRevision: async (id, value) => { sources.push(id); return { draft_id: `revision-${sources.length}`, plan: value }; },
    confirmDraft: async () => { if (++confirms === 1) throw Error("temporary"); }
  });
  f.markEdited(edited);
  await assert.rejects(f.confirm());
  f.markEdited({ ...edited, goal_title: "Another" });
  await f.confirm();
  assert.deepEqual(sources, ["original", "revision-1"]);
});

test("save failure retains edits and never confirms", async () => {
  let saves = 0;
  let confirms = 0;
  const f = await flow({
    saveRevision: async (id, value) => { assert.deepEqual(value, edited); if (++saves === 1) throw Error("save failed"); return { draft_id: "saved", plan: value }; },
    confirmDraft: async () => { confirms++; }
  });
  f.markEdited(edited);
  await assert.rejects(f.confirm(), /save failed/);
  assert.equal(confirms, 0);
  await f.confirm();
  assert.equal(confirms, 1);
});

test("overlapping submissions share one request", async () => {
  let finish;
  let confirms = 0;
  const f = await flow({ saveRevision: () => assert.fail("unchanged"), confirmDraft: () => {
    confirms++;
    return new Promise((resolve) => { finish = resolve; });
  } });
  const first = f.confirm();
  const second = f.confirm();
  await new Promise((resolve) => setImmediate(resolve));
  finish("created");
  assert.deepEqual(await Promise.all([first, second]), ["created", "created"]);
  assert.equal(confirms, 1);
});

test("missing generation ID and malformed revision never fall back to plan confirmation", async () => {
  const { createAiDraftFlow } = await import("../src/pages/aiDraftFlow.mjs");
  const f = createAiDraftFlow({ saveRevision: async () => ({ plan }), confirmDraft: () => assert.fail("unsafe confirmation") });
  assert.throws(() => f.setDraft({ plan }), /draft/i);
  await assert.rejects(f.confirm(), /draft/i);
  f.setDraft(draft);
  f.markEdited(edited);
  await assert.rejects(f.confirm(), /draft/i);
});

test("refresh failure is reported separately after successful confirmation", async () => {
  const { refreshAfterAiConfirmation } = await import("../src/pages/aiDraftFlow.mjs");
  const errors = [];
  let confirms = 0;
  const f = await flow({ confirmDraft: async () => { confirms++; } });
  await f.confirm();
  await refreshAfterAiConfirmation(async () => { throw Error("refresh failed"); }, (message) => errors.push(message));
  assert.equal(confirms, 1);
  assert.match(errors[0], /created.*refresh/i);
  await assert.rejects(f.confirm(), /draft/i);
});
