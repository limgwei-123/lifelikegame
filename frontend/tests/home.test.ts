import assert from 'node:assert/strict';
import { test } from 'node:test';
import { SessionController } from '../src/session/controller.ts';
import { HomeController } from '../src/features/home/controller.ts';
import type { Progress, TaskInstance, Task } from '../src/api/tasks.ts';
import type { User } from '../src/api/types.ts';

const user: User = { id: 'player', email: 'player@example.com', current_value: 0,
  display_name: null, avatar_key: 'leaf', timezone: 'Pacific/Kiritimati' };
const progress: Progress = { today: '2026-11-27', timezone: user.timezone, total_completed: 0, completed_today: 0,
  total_damage: 0, current_streak: 0, longest_streak: 0, defeated_bosses: 0,
  boss: { id: 'slime', name: '史莱姆', round: 1, position: 1, hp: 30, max_hp: 30 }, bosses: [] };
const task: Task = { id: 1, title: '走一走', description: null, goal_id: null, is_active: true,
  scoring_scheme_id: null, scoring_scheme_json: null, is_scoring_scheme_locked: false };
const instance: TaskInstance = { id: 1, user_id: user.id, task_id: 1, task_schedule_id: 1,
  date_instance: progress.today, status: 'todo', completion_level: null, score_awarded: 0,
  scoring_snapshot_json: null, generated_reason: 'recurring', deleted_at: null,
  created_at: '2026-11-26T20:00:00Z', updated_at: '2026-11-26T20:00:00Z' };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { resolve, promise }; }
async function fixture(intercept?: (path: string, init?: RequestInit) => Promise<Response | undefined>) {
  const paths: string[] = [];
  const session = new SessionController({ read: async () => null, write: async () => {} }, 'https://api.example.test', async (url, init) => {
    const path = new URL(String(url)).pathname + new URL(String(url)).search;
    paths.push(path);
    const custom = await intercept?.(path, init); if (custom) return custom;
    if (path === '/auth/login') return json({ access_token: 'token' });
    if (path === '/users/me') return json(user);
    if (path === '/progress') return json(progress);
    if (path === '/tasks') return json([task]);
    if (path === '/task_schedules') return json([{ id: 1, task_id: 1, schedule_type: 'daily', schedule_value_json: {}, start_date: progress.today, end_date: null }]);
    if (path.startsWith('/task_instances/pending')) return json([instance]);
    if (path.startsWith('/task_instances?')) return json(path.endsWith(progress.today) ? [instance] : []);
    if (path.startsWith('/task_instances/month')) return json([instance]);
    return json([]);
  });
  await session.signIn(user.email, 'password123');
  return { session, home: new HomeController(session), paths };
}

test('server today is authoritative and generation runs once per player day, never on date browsing', async () => {
  const { home, paths } = await fixture();
  await home.refresh(true); await home.refresh(true);
  assert.equal(home.getSnapshot().selectedDate, progress.today);
  assert.equal(paths.filter(p => p === '/tasks_instances/generate').length, 1);
  await home.selectDate('2026-12-01');
  assert.equal(home.getSnapshot().selectedDate, '2026-12-01');
  assert.equal(paths.filter(p => p === '/tasks_instances/generate').length, 1);
  assert.ok(paths.includes('/task_instances/month?year=2026&month=12'));
});

test('a late date read does not publish data for the previous selection', async () => {
  const blocked = deferred<Response>(), entered = deferred<void>();
  const { home } = await fixture(async path => {
    if (path === '/task_instances?date=2026-11-28') { entered.resolve(); return blocked.promise; }
  });
  await home.refresh();
  const first = home.selectDate('2026-11-28'); await entered.promise;
  const second = home.selectDate('2026-11-29');
  blocked.resolve(json([{ ...instance, id: 8, date_instance: '2026-11-28' }]));
  await Promise.all([first, second]);
  assert.equal(home.getSnapshot().selectedDate, '2026-11-29');
  assert.deepEqual(home.getSnapshot().data?.day, []);
});

test('completion is single-flight and reconciles server progress, balance and next occurrence', async () => {
  const reply = deferred<Response>(), entered = deferred<void>();
  const { home, session, paths } = await fixture(async path => {
    if (path.endsWith('/complete')) { entered.resolve(); return reply.promise; }
  });
  await home.refresh();
  const first = home.complete(instance); await entered.promise;
  assert.equal(await home.complete(instance), false);
  // Prevent a successful response from being overwritten by fixture's stale reads.
  reply.resolve(json({ task_instance: { ...instance, status: 'done' },
    next_task_instance: { ...instance, id: 2, date_instance: '2026-11-28' },
    user: { ...user, current_value: 7 }, point_ledger: { id: 1, delta: 7, entry_type: 'earn', source_type: 'task_instance', source_id: 1 },
    progress: { ...progress, completed_today: 1, current_streak: 1 } }));
  assert.equal(await first, true);
  assert.equal(paths.filter(p => p.endsWith('/complete')).length, 1);
  assert.equal(session.getSnapshot().user?.current_value, 7);
  assert.equal(home.getSnapshot().lastCompletion?.next_task_instance?.id, 2);
  assert.equal(home.getSnapshot().lastCompletion?.point_ledger?.delta, 7);
  assert.equal(await home.complete(instance), false);
  assert.equal(paths.filter(p => p.endsWith('/complete')).length, 1);
});

test('failed completion does not award progress or mark a task complete', async () => {
  const { home, session } = await fixture(async path => path.endsWith('/complete') ? json({}, 422) : undefined);
  await home.refresh();
  assert.equal(await home.complete(instance), false);
  assert.equal(home.getSnapshot().data?.day[0].status, 'todo');
  assert.equal(session.getSnapshot().user?.current_value, 0);
  assert.equal(home.getSnapshot().lastCompletion, null);
  assert.ok(home.getSnapshot().error);
});

test('logout discards a late mutation response and queued refreshes', async () => {
  const reply = deferred<Response>(), entered = deferred<void>();
  const { home, session } = await fixture(async path => {
    if (path.endsWith('/complete')) { entered.resolve(); return reply.promise; }
  });
  await home.refresh();
  const completing = home.complete(instance); await entered.promise;
  await session.logout();
  reply.resolve(json({ task_instance: { ...instance, status: 'done' }, next_task_instance: null,
    user: { ...user, current_value: 999 }, point_ledger: null, progress }));
  assert.equal(await completing, false);
  assert.equal(session.getSnapshot().user, null);
  assert.equal(home.getSnapshot().lastCompletion, null);
});

test('extending a schedule explicitly repairs its current occurrence even after same-day repair', async () => {
  const { home, paths } = await fixture(async (path, init) => path === '/task_schedules/1'
    ? json({ ...JSON.parse(String(init?.body)), id: 1, task_id: 1 }) : undefined);
  await home.refresh(true);
  assert.equal(await home.updateSchedule(1, { schedule_type: 'daily', schedule_value_json: {}, start_date: progress.today, end_date: '2026-12-31' }), true);
  assert.equal(paths.filter(p => p === '/tasks_instances/generate').length, 2);
});

test('a saved creation is not reported as failed when the following list refresh fails', async () => {
  let saved = false;
  const { home, paths } = await fixture(async path => {
    if (path === '/workflows/tasks') { saved = true; return json({ task: { ...task, id: 2 }, schedule: null, task_instance: null }, 201); }
    if (path === '/progress' && saved) throw new Error('connection interrupted');
  });
  await home.refresh();
  assert.equal(await home.create({ goal_id: null, task: { title: '买牛奶', description: null, scoring_scheme_id: null },
    schedule: { schedule_type: 'once', schedule_value_json: {}, start_date: progress.today, end_date: null } }), true);
  assert.match(home.getSnapshot().error!, /操作已保存/);
  assert.equal(paths.filter(p => p === '/workflows/tasks').length, 1);
});

test('future occurrences cannot be completed and failed date loads retain their actual loaded date', async () => {
  const { home, paths } = await fixture(async path => path === '/task_instances?date=2026-11-28' ? json({}, 500) : undefined);
  await home.refresh();
  assert.equal(await home.complete({ ...instance, date_instance: '2026-11-28' }), false);
  assert.equal(paths.filter(p => p.endsWith('/complete')).length, 0);
  await home.selectDate('2026-11-28');
  assert.equal(home.getSnapshot().selectedDate, '2026-11-28');
  assert.equal(home.getSnapshot().data?.date, progress.today);
  assert.ok(home.getSnapshot().error);
});

test('confirmed goal damage emits one feedback event; refresh and old dismissals cannot replay or erase it', async () => {
  const { home, paths } = await fixture(async path => {
    if (path === '/tasks') return json([{ ...task, goal_id: 2 }]);
    if (path.endsWith('/complete')) return json({ task_instance: { ...instance, status: 'done' }, next_task_instance: null,
      user, point_ledger: null, progress: { ...progress, total_completed: 1, total_damage: 1,
        boss: { ...progress.boss, hp: 29 } } });
  });
  await home.refresh();
  assert.equal(await home.complete(instance), true);
  const event = home.getSnapshot().feedback;
  assert.equal(event?.kind, 'hit');
  assert.equal(event?.instanceId, instance.id);
  assert.equal(await home.complete(instance), false);
  assert.equal(home.getSnapshot().feedback, event);
  home.clearFeedback(999); assert.equal(home.getSnapshot().feedback, event);
  home.clearFeedback(instance.id); assert.equal(home.getSnapshot().feedback, null);
  await home.refresh(); assert.equal(home.getSnapshot().feedback, null);
  assert.equal(paths.filter(p => p.endsWith('/complete')).length, 1);
});
