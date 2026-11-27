import assert from 'node:assert/strict';
import { test } from 'node:test';
import { addDays, monthGrid, shiftMonth, weekday, validDate } from '../src/features/tasks/dates.ts';
import { buildTaskPayload, completionLevels, visibleInstances } from '../src/features/tasks/model.ts';
import type { Task, TaskInstance } from '../src/api/tasks.ts';

const todo: Task = { id: 1, goal_id: null, title: '买牛奶', description: null, is_active: true,
  scoring_scheme_id: null, scoring_scheme_json: null, is_scoring_scheme_locked: false };
const occurrence = (id: number, day: string, status: TaskInstance['status'] = 'todo'): TaskInstance => ({
  id, user_id: 'player', task_id: 1, task_schedule_id: 1, date_instance: day, status,
  completion_level: null, score_awarded: 0, scoring_snapshot_json: null, generated_reason: 'recurring',
  created_at: `${day}T00:00:00Z`, updated_at: `${day}T00:00:00Z`, deleted_at: null,
});

test('calendar arithmetic handles month/year/leap boundaries without device timezone conversion', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2028-03-01', -1), '2028-02-29');
  assert.equal(shiftMonth('2026-01-31', 1), '2026-02-28');
  assert.equal(weekday('2026-11-23'), 0);
  assert.equal(validDate('2026-02-29'), false);
  assert.equal(validDate('2028-02-29'), true);
  const grid = monthGrid('2026-11-26');
  assert.equal(grid.filter(Boolean).length, 30);
  assert.equal(grid[6], '2026-11-01');
});

test('standalone payload never forwards a stale goal scoring selection', () => {
  const payload = buildTaskPayload({ title: ' 买牛奶 ', description: '', goalId: null, schemeId: 77,
    kind: 'once', start: '2026-11-26', end: '', days: [], monthDay: 26 });
  assert.equal(payload.goal_id, null);
  assert.equal(payload.task.scoring_scheme_id, null);
  assert.equal(payload.task.title, '买牛奶');
  assert.equal(payload.schedule.start_date, '2026-11-26');
  assert.equal(payload.schedule.end_date, null);
  assert.throws(() => buildTaskPayload({ title: ' ', description: '', goalId: null, schemeId: null,
    kind: 'daily', start: '2026-11-26', end: '', days: [], monthDay: 26 }));
});

test('weekly and monthly form validation matches the API contract', () => {
  const form = { title: '运动', description: '', goalId: 1, schemeId: 7, kind: 'weekly' as const,
    start: '2026-11-26', end: '2026-12-31', days: [6, 0, 0], monthDay: 31 };
  assert.deepEqual(buildTaskPayload(form).schedule.schedule_value_json, { days: [0, 6] });
  assert.throws(() => buildTaskPayload({ ...form, days: [] }));
  assert.throws(() => buildTaskPayload({ ...form, end: '2026-11-01' }));
  assert.deepEqual(buildTaskPayload({ ...form, kind: 'monthly' }).schedule.schedule_value_json, { day: 31 });
  assert.throws(() => buildTaskPayload({ ...form, kind: 'monthly', monthDay: 32 }));
});

test('scoring uses occurrence snapshot and no-goal tasks have no scoring fallback', () => {
  const item = { ...occurrence(1, '2026-11-26'), scoring_snapshot_json: { '完成': 3, '认真完成': 7 } };
  assert.deepEqual(completionLevels(todo, item), []);
  const scored = { ...todo, goal_id: 2, scoring_scheme_json: { '新方案': 100 } };
  assert.deepEqual(completionLevels(scored, item), [['完成', 3], ['认真完成', 7]]);
  assert.deepEqual(completionLevels(scored, { ...item, scoring_snapshot_json: null }), []);
});

test('today merges unique pending work with dated history; other dates do not carry overdue work', () => {
  const overdue = occurrence(1, '2026-11-20');
  const current = occurrence(2, '2026-11-26');
  const done = occurrence(3, '2026-11-26', 'done');
  const ghost = { ...occurrence(4, '2026-11-26'), task_id: 99 };
  assert.deepEqual(visibleInstances('2026-11-26', '2026-11-26', [current, done, ghost], [overdue, current], [todo]).map(x => x.id), [1, 2, 3]);
  assert.deepEqual(visibleInstances('2026-11-27', '2026-11-26', [occurrence(5, '2026-11-27')], [overdue], [todo]).map(x => x.id), [5]);
  assert.deepEqual(visibleInstances('2026-11-26', '2026-11-26', [done], [overdue], [{ ...todo, is_active: false }]).map(x => x.id), [3]);
});

test('failed date changes cannot expose another date and deleted task completions remain history', () => {
  const old = occurrence(1, '2026-11-26');
  assert.deepEqual(visibleInstances('2026-11-25', '2026-11-26', [old], [], [todo]), []);
  const deleted = { ...old, id: 8, task_id: 999, status: 'done' as const };
  assert.deepEqual(visibleInstances('2026-11-26', '2026-11-26', [deleted], [], []).map(i => i.id), [8]);
});
