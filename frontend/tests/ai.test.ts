import assert from 'node:assert/strict';
import { test } from 'node:test';
import { SessionController } from '../src/session/controller.ts';
import { AIController } from '../src/features/ai/controller.ts';
import { draftPlan, generatedResponse } from '../src/features/ai/model.ts';

const id = '11111111-1111-4111-8111-111111111111', revisedId = '22222222-2222-4222-8222-222222222222';
const plan = { goal_title: '运动', tasks: [{ title: '快走', description: null, scoring_scheme_id: null, schedule_type: 'weekly' as const, schedule_value_json: { days: [0, 2, 4] } }] };
const ready = { status: 'plan_ready', message: '准备好了', questions: [], plan, draft_id: id, conversation_history: [{ role: 'user', content: '运动' }, { role: 'assistant', content: '准备好了' }] };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
function deferred<T>() { let resolve!: (x: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { resolve, promise }; }
async function fixture(intercept?: (path: string, body: any) => Promise<Response | undefined>, confirmation: () => Promise<any> = async () => 'confirmed') {
  const calls: { path: string; body: any }[] = [];
  const session = new SessionController({ read: async () => null, write: async () => {} }, 'https://api.test', async (url, options) => {
    const path = new URL(String(url)).pathname, body = options?.body ? JSON.parse(String(options.body)) : null;
    calls.push({ path, body }); const custom = await intercept?.(path, body); if (custom) return custom;
    if (path === '/auth/login') return json({ access_token: 'test-token' });
    if (path === '/users/me') return json({ id: 'player', email: 'ai@example.com', current_value: 0, display_name: null, avatar_key: 'leaf', timezone: 'Asia/Kuala_Lumpur' });
    if (path.endsWith('/revisions')) return json({ draft_id: revisedId, plan: body });
    return json(ready);
  });
  await session.signIn('ai@example.com', 'test-password');
  const confirmedIds: string[] = [];
  const ai = new AIController(session, async draftId => { confirmedIds.push(draftId); return confirmation(); });
  return { ai, session, calls, confirmedIds };
}
test('draft validation matches 1–3 daily/weekly tasks and safe owned scheme IDs', () => {
  assert.deepEqual(draftPlan(plan), plan);
  for (const bad of [{ ...plan, tasks: [] }, { ...plan, tasks: Array(4).fill(plan.tasks[0]) }, { ...plan, goal_title: ' ' },
    { ...plan, tasks: [{ ...plan.tasks[0], schedule_type: 'monthly' }] }, { ...plan, tasks: [{ ...plan.tasks[0], schedule_value_json: { days: [] } }] },
    { ...plan, tasks: [{ ...plan.tasks[0], scoring_scheme_id: -1 }] }]) assert.throws(() => draftPlan(bad));
  assert.throws(() => generatedResponse({ ...ready, draft_id: null }));
  assert.throws(() => generatedResponse({ ...ready, status: 'need_more_info' }));
});
test('follow-up uses returned history; generation alone never confirms a goal', async () => {
  let count = 0;
  const { ai, calls, confirmedIds } = await fixture(async path => path.endsWith('generate-plan') && count++ === 0
    ? json({ status: 'need_more_info', message: '每周哪几天？', questions: ['哪几天运动？'], plan: null, draft_id: null, conversation_history: ready.conversation_history }) : undefined);
  assert.equal(await ai.generate('想运动'), true); assert.equal(ai.getSnapshot().draft, null);
  await ai.generate('周一三五');
  assert.deepEqual(calls.filter(c => c.path.endsWith('generate-plan'))[1].body.conversation_history, ready.conversation_history);
  assert.equal(ai.getSnapshot().draft?.draft_id, id); assert.deepEqual(confirmedIds, []);
});
test('generation deadline covers all backend SDK attempts and backoff', async t => {
  const { ai, session } = await fixture();
  const original = session.api.request.bind(session.api);
  let deadline: number | undefined;
  t.mock.method(session.api, 'request', function<T>(path: string, options: Parameters<typeof session.api.request>[1]) {
    if (path.endsWith('generate-plan')) deadline = options?.timeoutMs;
    return original<T>(path, options);
  });
  await ai.generate('运动');
  assert.ok(deadline !== undefined && deadline >= 70000, 'Three 20s attempts plus backoff must fit the frontend deadline');
});
test('edited plan saves revision first and confirms only its returned ID once', async () => {
  const gate = deferred<any>(); const { ai, calls, confirmedIds } = await fixture(undefined, () => gate.promise);
  await ai.generate('运动'); const edited = { ...plan, goal_title: '坚持运动' };
  const saving = ai.confirm(edited); await new Promise(r => setImmediate(r));
  assert.equal(await ai.confirm(edited), false); assert.deepEqual(confirmedIds, [revisedId]);
  assert.deepEqual(calls.find(c => c.path.endsWith('/revisions'))?.body, edited);
  gate.resolve('confirmed'); assert.equal(await saving, true); assert.equal(ai.getSnapshot().outcome, 'confirmed');
  assert.equal(await ai.confirm(edited), false);
});
test('uncertain confirmation retries the same ID without saving a new revision', async () => {
  let attempt = 0; const { ai, calls, confirmedIds } = await fixture(undefined, async () => attempt++ ? 'consumed' : 'retry');
  await ai.generate('运动'); assert.equal(await ai.confirm(plan), false);
  assert.equal(ai.getSnapshot().pendingId, revisedId);
  assert.equal(await ai.confirm({ ...plan, goal_title: '不能另建' }), false);
  assert.equal(await ai.retryConfirmation(), true);
  assert.deepEqual(confirmedIds, [revisedId, revisedId]); assert.equal(calls.filter(c => c.path.endsWith('/revisions')).length, 1);
  assert.equal(ai.getSnapshot().outcome, 'consumed');
});
test('quota failure preserves the draft and a late response cannot publish after logout', async () => {
  const reply = deferred<Response>(), entered = deferred<void>(); let mode = 'ok';
  const { ai, session } = await fixture(async path => {
    if (!path.endsWith('generate-plan')) return;
    if (mode === 'quota') return json({ code: 'AI_DAILY_LIMIT_EXCEEDED' }, 429);
    if (mode === 'late') { entered.resolve(undefined); return reply.promise; }
  });
  await ai.generate('运动'); mode = 'quota'; assert.equal(await ai.generate('调整'), false);
  assert.equal(ai.getSnapshot().draft?.draft_id, id); assert.match(ai.getSnapshot().error!, /今日/);
  mode = 'late'; const pending = ai.generate('迟到'); await entered.promise;
  await session.logout(); await session.signIn('ai@example.com', 'new-password'); reply.resolve(json({ ...ready, message: '不应显示' }));
  assert.equal(await pending, false); assert.ok(!JSON.stringify(ai.getSnapshot()).includes('不应显示'));
});
