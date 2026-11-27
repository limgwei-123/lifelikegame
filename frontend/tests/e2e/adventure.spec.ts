import { test, expect } from '@playwright/test';
import type { Progress } from '../../src/api/tasks';

test.skip(process.env.E2E_DISPOSABLE_API !== '1', 'Requires an isolated disposable backend');
test('real boss hits, defeat, second round, reduced motion and account isolation', async ({ page, request }, testInfo) => {
  test.setTimeout(240_000);
  const api = process.env.E2E_API_URL || 'http://localhost:8001';
  const email = `boss-${Date.now()}@example.com`, password = 'Review-only-Password2026!';
  const signup = await request.post(`${api}/auth/signup`, { data: { email, password } });
  expect(signup.status()).toBe(201);
  const auth = await request.post(`${api}/auth/login`, { data: { email, password } }); expect(auth.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await auth.json()).access_token}` };
  const get = async (path: string) => { const result = await request.get(api + path, { headers }); expect(result.ok()).toBeTruthy(); return result.json(); };
  const post = async (path: string, data: unknown) => {
    const result = await request.post(api + path, { headers, data }); expect(result.ok(), `${path}: ${await result.text()}`).toBeTruthy(); return result.json();
  };
  const initial: Progress = await get('/progress');
  const goal = await post('/goals', { title: '我的冒险目标' });
  const scheme = await post('/scoring_schemes', { title: '一步一分', levels_json: { '完成': 1 } });
  const create = async (title: string, scored = true) => post('/workflows/tasks', {
    goal_id: scored ? goal.id : null,
    task: { title, scoring_scheme_id: scored ? scheme.id : null },
    schedule: { schedule_type: 'once', schedule_value_json: {}, start_date: initial.today },
  });
  await create('普通待办', false); await create('第一步'); await create('第二步');
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/login');
  await page.getByLabel('邮箱', { exact: true }).fill(email); await page.getByLabel('密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const ready = () => expect(page.getByRole('button', { name: '添加任务', exact: true })).toBeEnabled();
  await ready();
  await expect(page.getByTestId('home-boss-hp')).toHaveText('2 / 2');
  await page.getByRole('checkbox', { name: '完成 普通待办', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: '完成 普通待办', exact: true })).toBeChecked();
  await expect(page.getByTestId('adventure-feedback')).toBeHidden();
  await expect(page.getByTestId('home-boss-hp')).toHaveText('2 / 2');
  await ready(); await page.getByRole('checkbox', { name: '完成 第一步', exact: true }).click();
  await expect(page.getByTestId('home-boss-hp')).toHaveText('1 / 2');
  await expect(page.getByTestId('adventure-feedback')).toContainText('命中！-1 HP');
  await page.getByRole('button', { name: '收起冒险反馈' }).click();
  await page.getByRole('button', { name: '查看冒险', exact: true }).click();
  await expect(page.getByTestId('adventure-boss-hp')).toHaveText('1 / 2');
  await expect(page.getByTestId('boss-roster-slime')).toContainText('挑战中');
  await expect(page.getByTestId('boss-roster-cloud')).toContainText('待挑战');
  await expect(page.getByTestId('adventure-feedback')).toBeHidden();
  await page.getByRole('tab', { name: '首页', exact: true }).click(); await ready();
  await page.getByRole('checkbox', { name: '完成 第二步', exact: true }).click();
  await expect(page.getByTestId('adventure-feedback')).toContainText('击败了软糖史莱姆');
  await expect(page.getByTestId('home-boss-hp')).toHaveText('4 / 4');
  await page.getByRole('button', { name: '收起冒险反馈' }).click();
  await page.getByRole('tab', { name: '冒险', exact: true }).click();
  await expect(page.getByTestId('current-boss')).toContainText('困困云怪');
  await expect(page.getByTestId('boss-roster-slime')).toContainText('已通过');
  await expect(page.getByTestId('boss-roster-cloud')).toContainText('挑战中');
  await expect(page.getByRole('button', { name: '刷新冒险' })).toBeEnabled();
  await page.screenshot({ path: testInfo.outputPath('adventure-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('heading', { name: '我的冒险', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('adventure-phone.png'), fullPage: true });
  // Advance using real public workflow/completion APIs in this disposable
  // account. Never mutate the original development DB or fabricate progress.
  for (let damage = 3; damage <= 74; damage++) {
    const created = await create(`冒险准备 ${damage}`);
    await post(`/task_instances/${created.task_instance.id}/complete`, {});
  }
  const dragon: Progress = await get('/progress');
  expect(dragon.boss.id).toBe('dragon'); expect(dragon.boss.hp).toBe(1);
  await page.getByRole('button', { name: '刷新冒险' }).click();
  await expect(page.getByTestId('adventure-boss-hp')).toHaveText('1 / 30');
  await create('小龙的最后一步');
  await page.getByRole('tab', { name: '首页', exact: true }).click(); await ready();
  await page.getByRole('checkbox', { name: '完成 小龙的最后一步', exact: true }).click();
  await expect(page.getByTestId('adventure-feedback')).toContainText('击败了皇冠小龙');
  await expect(page.getByTestId('home-boss-hp')).toHaveText('32 / 32');
  const round2: Progress = await get('/progress'); expect(round2.boss.round).toBe(2);
  await page.getByRole('button', { name: '收起冒险反馈' }).click();
  await page.getByRole('tab', { name: '冒险', exact: true }).click();
  await expect(page.getByTestId('current-boss')).toContainText('第 2 轮');
  await expect(page.getByTestId('adventure-boss-hp')).toHaveText(`${round2.boss.hp} / ${round2.boss.max_hp}`);
  for (const boss of round2.bosses) await expect(page.getByTestId(`boss-roster-${boss.id}`)).toContainText(`${boss.max_hp} HP`);
  await page.reload();
  await expect(page.getByTestId('adventure-boss-hp')).toHaveText('32 / 32');
  await expect(page.getByTestId('adventure-feedback')).toBeHidden();
  // Another actual player's session must start with its own zero progress.
  const other = `boss-other-${Date.now()}@example.com`;
  expect((await request.post(`${api}/auth/signup`, { data: { email: other, password } })).status()).toBe(201);
  await page.getByRole('tab', { name: '我的', exact: true }).click();
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await page.getByLabel('邮箱', { exact: true }).fill(other); await page.getByLabel('密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click(); await ready();
  await expect(page.getByTestId('home-boss-hp')).toHaveText('2 / 2');
  await expect(page.getByTestId('adventure-feedback')).toBeHidden();
  expect(errors).toEqual([]);
});
