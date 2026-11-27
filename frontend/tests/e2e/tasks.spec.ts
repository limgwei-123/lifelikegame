import { test, expect, type Page } from '@playwright/test';
import { addDays, weekday } from '../../src/features/tasks/dates';
import type { CreatedTask, Progress, Task } from '../../src/api/tasks';

test.skip(process.env.E2E_DISPOSABLE_API !== '1', 'Requires an isolated disposable backend');

test('real home workflow: todo, scoring snapshots, recurrence, dates, edits, pause and delete', async ({ page, request }, testInfo) => {
  test.setTimeout(180_000);
  const api = process.env.E2E_API_URL || 'http://localhost:8001';
  const email = 'tasks-browser@example.com', password = 'Review-only-Password2026!';
  const signup = await request.post(`${api}/auth/signup`, { data: { email, password } });
  expect([201, 409]).toContain(signup.status());
  const auth = await request.post(`${api}/auth/login`, { data: { email, password } });
  expect(auth.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await auth.json()).access_token}` };
  const get = async (path: string) => { const r = await request.get(api + path, { headers }); expect(r.ok()).toBeTruthy(); return r.json(); };
  const post = async (path: string, data: unknown) => {
    const r = await request.post(api + path, { headers, data }); expect(r.ok(), `${path}: ${await r.text()}`).toBeTruthy(); return r.status() === 204 ? null : r.json();
  };
  for (const task of await get('/tasks') as Task[]) if (task.title.startsWith('E2E ')) await post(`/tasks/${task.id}/delete`, {});
  const before: Progress = await get('/progress'), today = before.today, yesterday = addDays(today, -1), tomorrow = addDays(today, 1);
  const balance = (await get('/users/me')).current_value;
  const run = Date.now();
  const goal = await post('/goals', { title: `E2E 运动目标 ${run}` });
  const single = await post('/scoring_schemes', { title: `E2E 单档 ${run}`, levels_json: { '完成': 3 } });
  const multi = await post('/scoring_schemes', { title: `E2E 多档 ${run}`, levels_json: { '轻量': 2, '认真': 7 } });
  // Seed only existing management features (their UI belongs to package 5).
  const overdue = await post('/workflows/tasks', { goal_id: null, task: { title: 'E2E 逾期待办' },
    schedule: { schedule_type: 'once', schedule_value_json: {}, start_date: yesterday } });
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/login');
  await page.getByLabel('邮箱', { exact: true }).fill(email);
  await page.getByLabel('密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const ready = () => expect(page.getByRole('button', { name: '添加任务', exact: true })).toBeEnabled();
  await ready();
  await expect(page.getByText(/逾期 ·/)).toBeVisible();
  const create = async (title: string, setup?: () => Promise<void>): Promise<CreatedTask> => {
    await ready();
    await page.getByRole('button', { name: '添加任务', exact: true }).click();
    await page.getByLabel('任务名称', { exact: true }).fill(title);
    await setup?.();
    const response = page.waitForResponse(r => r.url() === `${api}/workflows/tasks` && r.request().method() === 'POST');
    await page.getByRole('dialog', { name: '添加任务', exact: true }).getByRole('button', { name: '添加任务', exact: true }).click();
    const result = await response; expect(result.ok(), await result.text()).toBeTruthy();
    await expect(page.getByRole('heading', { name: '添加任务', exact: true })).toBeHidden();
    await ready(); return result.json();
  };
  const complete = async (title: string, disappears = false) => {
    await ready(); await page.getByRole('checkbox', { name: `完成 ${title}`, exact: true }).click();
    if (disappears) await expect(page.getByRole('checkbox', { name: `完成 ${title}`, exact: true })).toBeHidden();
    else await expect(page.getByRole('checkbox', { name: `完成 ${title}`, exact: true })).toBeChecked();
  };
  const ordinary = await create('E2E 买牛奶');
  expect(ordinary.task.goal_id).toBeNull(); expect(ordinary.task.scoring_scheme_json).toBeNull();
  await complete('E2E 买牛奶');
  expect((await get('/users/me')).current_value).toBe(balance);
  expect((await get('/progress')).total_damage).toBe(before.total_damage);
  await complete('E2E 逾期待办', true);
  await expect(page.getByTestId(`task-instance-${overdue.task_instance.id}`)).toBeHidden();
  expect((await get('/progress')).completed_today).toBe(before.completed_today + 2);
  await create('E2E 单档任务', async () => {
    await page.getByRole('button', { name: goal.title, exact: true }).click();
    await page.getByRole('button', { name: single.title, exact: true }).click();
  });
  await complete('E2E 单档任务');
  await expect(page.getByRole('heading', { name: '完成情况' })).toBeHidden();
  const scored = await create('E2E 多档任务', async () => {
    await page.getByRole('button', { name: goal.title, exact: true }).click();
    await page.getByRole('button', { name: multi.title, exact: true }).click();
  });
  await post(`/scoring_schemes/${multi.id}`, { levels_json: { '已修改': 99 } });
  await page.getByRole('button', { name: '刷新任务' }).click(); await ready();
  await page.getByRole('checkbox', { name: '完成 E2E 多档任务', exact: true }).click();
  await expect(page.getByRole('button', { name: '认真 · +7 分', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '认真 · +7 分', exact: true }).click();
  await expect(page.getByRole('heading', { name: '完成情况' })).toBeHidden();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 多档任务', exact: true })).toBeChecked();
  expect((await get('/users/me')).current_value).toBe(balance + 10);
  expect((await get('/progress')).total_damage).toBe(before.total_damage + 2);
  const daily = await create('E2E 每日散步', async () => { await page.getByRole('button', { name: '每天', exact: true }).click(); });
  await complete('E2E 每日散步');
  const future = await get(`/task_instances?date=${tomorrow}`);
  expect(future.filter((i: { task_id: number }) => i.task_id === daily.task.id)).toHaveLength(1);
  await pickHomeDate(page, tomorrow, today); await ready();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 每日散步', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: '今天', exact: true }).click(); await ready();
  const failing = await create('E2E 失败保留');
  const progressBeforeFailure = await get('/progress');
  await page.route(`**/task_instances/${failing.task_instance!.id}/complete`, route => route.fulfill({ status: 422, json: { code: 'VALIDATION_ERROR' } }));
  await page.getByRole('checkbox', { name: '完成 E2E 失败保留', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: '请检查填写的信息后再试。' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 失败保留', exact: true })).not.toBeChecked();
  expect((await get('/progress')).total_completed).toBe(progressBeforeFailure.total_completed);
  await page.unroute(`**/task_instances/${failing.task_instance!.id}/complete`);
  await page.getByRole('button', { name: '管理 E2E 失败保留', exact: true }).click();
  await page.getByRole('button', { name: '编辑任务', exact: true }).click();
  await page.getByLabel('任务名称', { exact: true }).fill('E2E 已改名');
  await page.getByRole('button', { name: '保存修改', exact: true }).click(); await ready();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 已改名', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '管理 E2E 已改名', exact: true }).click();
  await page.getByRole('button', { name: '暂停任务', exact: true }).click(); await ready();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 已改名', exact: true })).toBeHidden();
  await page.getByRole('button', { name: '已暂停的任务' }).click();
  await page.getByRole('button', { name: '管理 E2E 已改名', exact: true }).click();
  await page.getByRole('button', { name: '恢复任务', exact: true }).click(); await ready();
  await page.getByRole('button', { name: '管理 E2E 已改名', exact: true }).click();
  await page.getByRole('button', { name: '删除任务', exact: true }).click();
  await page.getByRole('button', { name: '确认删除', exact: true }).click(); await ready();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 已改名', exact: true })).toBeHidden();
  const weekly = await create('E2E 每周拉伸', async () => { await page.getByRole('button', { name: '每周', exact: true }).click(); });
  expect(weekly.schedule!.schedule_value_json.days).toEqual([weekday(today)]);
  const monthly = await create('E2E 每月整理', async () => { await page.getByRole('button', { name: '每月', exact: true }).click(); });
  expect(monthly.schedule!.schedule_value_json.day).toBe(Number(today.slice(8)));
  // Date entry is shared by Web and native; test the actual nested calendar.
  const dated = await create('E2E 未来待办', async () => {
    await page.getByRole('button', { name: '任务日期', exact: true }).click();
    const delta = Number(tomorrow.slice(5, 7)) - Number(today.slice(5, 7));
    if (delta) await page.getByRole('button', { name: '下个月', exact: true }).click();
    await page.getByRole('dialog', { name: '选择日期', exact: true }).getByRole('button', { name: tomorrow, exact: true }).click();
  });
  expect(dated.task_instance!.date_instance).toBe(tomorrow);
  await expect(page.getByRole('checkbox', { name: '完成 E2E 未来待办', exact: true })).toBeHidden();
  // A completed deleted task must remain visible after a fresh server load.
  await page.getByRole('button', { name: '管理 E2E 买牛奶', exact: true }).click();
  await page.getByRole('button', { name: '删除任务', exact: true }).click();
  await page.getByRole('button', { name: '确认删除', exact: true }).click(); await ready();
  await expect(page.getByTestId(`task-instance-${ordinary.task_instance!.id}`).getByText('已删除的任务')).toBeVisible();
  await page.getByRole('button', { name: '打开月历' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('home-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: '打开月历' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('home-phone.png'), fullPage: true });
  await page.getByRole('button', { name: '添加任务', exact: true }).click();
  await expect(page.getByRole('dialog', { name: '添加任务', exact: true })).toBeVisible();
  await page.waitForTimeout(350); // Capture the settled RN Modal fade, not an intermediate frame.
  await page.screenshot({ path: testInfo.outputPath('form-phone.png'), fullPage: true });
  await page.getByRole('button', { name: '关闭', exact: true }).click();
  await page.reload(); await ready();
  await expect(page.getByRole('checkbox', { name: '完成 E2E 多档任务', exact: true })).toBeChecked();
  expect((await get(`/task_instances?date=${today}`)).find((i: { id: number }) => i.id === scored.task_instance!.id).score_awarded).toBe(7);
  expect(errors).toEqual([]);
});

async function pickHomeDate(page: Page, date: string, current: string) {
  await page.getByRole('button', { name: '打开月历' }).click();
  const distance = (Number(date.slice(0, 4)) - Number(current.slice(0, 4))) * 12 + Number(date.slice(5, 7)) - Number(current.slice(5, 7));
  for (let step = 0; step < Math.abs(distance); step++) await page.getByRole('button', { name: distance > 0 ? '下个月' : '上个月', exact: true }).click();
  await page.getByRole('dialog', { name: '选择日期', exact: true }).getByRole('button', { name: date, exact: true }).click();
}
