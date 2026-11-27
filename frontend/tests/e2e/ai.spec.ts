import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

test.skip(process.env.E2E_DISPOSABLE_API !== '1', 'Requires the isolated Docker frontend review backend');
test('AI review: follow-up, edited saved revision, real confirmation and uncertain-result recovery', async ({ page, request }, testInfo) => {
  test.setTimeout(150_000);
  const api = process.env.E2E_API_URL || 'http://localhost:8001';
  const email = `ai-browser-${Date.now()}@example.com`, password = 'Review-only-Password2026!';
  expect((await request.post(`${api}/auth/signup`, { data: { email, password } })).status()).toBe(201);
  const login = await request.post(`${api}/auth/login`, { data: { email, password } }); expect(login.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const get = async (path: string) => { const r = await request.get(api + path, { headers }); expect(r.ok()).toBeTruthy(); return r.json(); };
  const user = await get('/users/me');
  const schemeResponse = await request.post(`${api}/scoring_schemes`, { headers, data: { title: 'AI 测试评分', levels_json: { '完成': 3 } } });
  expect(schemeResponse.status()).toBe(201); const scheme = await schemeResponse.json();
  const plan = { goal_title: '运动习惯', tasks: [
    { title: '每日快走', description: '轻松开始', schedule_type: 'daily', schedule_value_json: {} },
    { title: '每周拉伸', description: null, schedule_type: 'weekly', schedule_value_json: { days: [0, 2, 4] } },
  ] };
  // Simulate only the vendor result; draft persistence uses the backend service
  // and actual revisions/confirmation below use the authenticated HTTP APIs.
  const script = readFileSync('tests/e2e/seed-ai-draft.py', 'utf8');
  const saved = JSON.parse(execFileSync('docker', ['exec', '-i', 'lifelikegame-frontend-review-api', 'python', '-c', script],
    { input: JSON.stringify({ user_id: user.id, plan }), encoding: 'utf8', timeout: 30_000 }));
  let generation = 0, quota = false; const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/ai-planner/generate-plan', async route => {
    const body = route.request().postDataJSON();
    if (quota) return route.fulfill({ status: 429, json: { code: 'AI_DAILY_LIMIT_EXCEEDED' } });
    if (generation++ === 0) return route.fulfill({ json: { status: 'need_more_info', message: '每周哪几天有时间？', questions: ['每次可以运动多久？'], plan: null, draft_id: null,
      conversation_history: [{ role: 'user', content: body.user_prompt }, { role: 'assistant', content: '每次多久？' }] } });
    expect(body.conversation_history).toHaveLength(2);
    return route.fulfill({ json: { status: 'plan_ready', message: '先从两个小任务开始。', questions: [], plan: saved.plan, draft_id: saved.draft_id,
      conversation_history: [...body.conversation_history, { role: 'user', content: body.user_prompt }, { role: 'assistant', content: '计划已准备好' }] } });
  });
  await page.goto('/login'); await page.getByLabel('邮箱', { exact: true }).fill(email); await page.getByLabel('密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('button', { name: '添加任务', exact: true })).toBeEnabled();
  await page.getByRole('tab', { name: '我的', exact: true }).click(); await page.getByRole('button', { name: 'AI 规划', exact: true }).click();
  await page.getByLabel('你的目标', { exact: true }).fill('想开始运动'); await page.getByRole('button', { name: '生成计划', exact: true }).click();
  await expect(page.getByText(/每次可以运动多久/)).toBeVisible();
  await page.getByLabel('补充或调整计划', { exact: true }).fill('周一三五，每次半小时'); await page.getByRole('button', { name: '发送补充', exact: true }).click();
  await expect(page.getByLabel('目标名称', { exact: true })).toHaveValue('运动习惯');
  expect(await get('/goals')).toHaveLength(0); expect(await get('/tasks')).toHaveLength(0);
  quota = true;
  await page.getByLabel('补充或调整计划', { exact: true }).fill('调整得更轻松'); await page.getByRole('button', { name: '发送补充', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: '今日 AI 额度' })).toBeVisible();
  await expect(page.getByLabel('补充或调整计划', { exact: true })).toHaveValue('调整得更轻松');
  await page.getByLabel('目标名称', { exact: true }).fill('坚持运动');
  await page.getByLabel('任务 1 名称', { exact: true }).fill('每天散步');
  await page.getByRole('button', { name: '任务 1 AI 测试评分', exact: true }).click();
  await page.getByRole('button', { name: '添加一个任务', exact: true }).click();
  await expect(page.getByRole('button', { name: '添加一个任务', exact: true })).toBeHidden();
  await page.getByRole('button', { name: '移除任务 3', exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath('ai-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 }); await page.emulateMedia({ colorScheme: 'dark' });
  await page.getByRole('heading', { name: '你的行动计划', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('ai-phone-dark.png'), fullPage: true });
  const confirmationIds: string[] = [], revisions: string[] = []; let loseFirstResponse = true;
  page.on('request', r => { if (r.method() === 'POST' && /\/revisions$/.test(r.url())) revisions.push(r.url()); });
  await page.route('**/workflows/ai/confirm', async route => {
    const body = route.request().postDataJSON(); expect(Object.keys(body)).toEqual(['draft_id']);
    confirmationIds.push(body.draft_id);
    const response = await route.fetch();
    if (loseFirstResponse) { expect(response.status()).toBe(201); loseFirstResponse = false; return route.abort('failed'); }
    expect(response.status()).toBe(409); return route.fulfill({ response });
  });
  await page.getByRole('button', { name: '确认创建计划', exact: true }).click();
  await page.getByRole('dialog', { name: '确认行动计划', exact: true }).getByRole('button', { name: '创建目标和任务', exact: true }).click();
  await expect(page.getByRole('dialog', { name: '确认行动计划', exact: true })).toBeHidden();
  await expect(page.getByRole('button', { name: '重新核实创建结果', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: '重新核实创建结果', exact: true }).click();
  await expect(page.getByRole('button', { name: '查看首页任务', exact: true })).toBeVisible();
  expect(revisions).toHaveLength(1); expect(confirmationIds).toHaveLength(2);
  expect(confirmationIds[0]).not.toBe(saved.draft_id); expect(confirmationIds[1]).toBe(confirmationIds[0]);
  const goals = await get('/goals'), tasks = await get('/tasks');
  expect(goals).toHaveLength(1); expect(goals[0].title).toBe('坚持运动'); expect(tasks).toHaveLength(2);
  expect(tasks.find((t: { title: string }) => t.title === '每天散步').scoring_scheme_id).toBe(scheme.id);
  await page.getByRole('button', { name: '查看首页任务', exact: true }).click();
  await expect(page.getByRole('button', { name: '添加任务', exact: true })).toBeEnabled();
  await expect(page.getByRole('checkbox', { name: '完成 每天散步', exact: true })).toBeVisible();
  await page.getByRole('checkbox', { name: '完成 每天散步', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: '完成 每天散步', exact: true })).toBeChecked();
  expect((await get('/users/me')).current_value).toBe(3);
  expect(errors).toEqual([]);
});
