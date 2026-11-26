import { test, expect } from '@playwright/test';

// Opt in explicitly: signup creates a user and must target a disposable API.
test.skip(process.env.E2E_DISPOSABLE_API !== '1', 'Requires an isolated disposable backend');

test('real registration, login, navigation, restore, expiry and logout', async ({ page }, testInfo) => {
  const email = `frontend-${Date.now()}@example.com`;
  const password = 'Review-only-Password2026!';
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/me');
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('desktop-login.png') });
  await page.getByRole('link', { name: '创建账号' }).click();
  await page.getByRole('textbox', { name: '邮箱', exact: true }).fill(email);
  await page.getByLabel('密码', { exact: true }).filter({ visible: true }).fill(password);
  await page.getByLabel('确认密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '创建账号', exact: true }).click();
  await expect(page.getByText('注册成功，请登录。')).toBeVisible();
  await page.getByLabel('密码', { exact: true }).filter({ visible: true }).fill('wrong-password');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByText('邮箱或密码不正确。')).toBeVisible();
  await page.getByLabel('密码', { exact: true }).filter({ visible: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('tab', { name: '首页' })).toBeVisible();
  await page.getByRole('tab', { name: '冒险', exact: true }).click();
  await expect(page.getByRole('heading', { name: '我的冒险' })).toBeVisible();
  await page.getByRole('tab', { name: '我的', exact: true }).click();
  await expect(page.getByText(email, { exact: true }).last()).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('desktop-account.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('tab', { name: '首页' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('phone-account.png') });
  await page.getByRole('button', { name: '退出登录' }).click();
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible();
  await page.goto('/adventure');
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible();
  await page.getByLabel('邮箱', { exact: true }).fill(email);
  await page.getByLabel('密码', { exact: true }).filter({ visible: true }).fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('tab', { name: '首页' })).toBeVisible();
  // The backend does not expose a test expiry route: simulate that single
  // boundary response, retaining real API calls for the rest of the workflow.
  await page.route('**/users/me', route => route.fulfill({ status: 401, json: { code: 'UNAUTHORIZED' } }));
  await page.reload();
  await expect(page.getByText('登录已失效，请重新登录。')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('lifelikegame_access_token'))).toBeNull();
  await page.screenshot({ path: testInfo.outputPath('phone-login.png') });
  expect(errors).toEqual([]);
});
