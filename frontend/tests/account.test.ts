import assert from 'node:assert/strict';
import { test } from 'node:test';
import { profilePayload, passwordErrors } from '../src/features/account/model.ts';
import { AppearanceController, decodePreferences } from '../src/theme/controller.ts';

test('profile normalizes optional nickname and validates backend avatar/timezone constraints', () => {
  assert.deepEqual(profilePayload({ name: '  小勇者  ', avatar: 'book', timezone: 'Asia/Kuala_Lumpur' }),
    { display_name: '小勇者', avatar_key: 'book', timezone: 'Asia/Kuala_Lumpur' });
  assert.equal(profilePayload({ name: '  ', avatar: 'leaf', timezone: 'UTC' }).display_name, null);
  assert.throws(() => profilePayload({ name: 'a'.repeat(31), avatar: 'leaf', timezone: 'UTC' }));
  assert.throws(() => profilePayload({ name: '名字', avatar: 'unknown', timezone: 'UTC' }));
  assert.throws(() => profilePayload({ name: '名字', avatar: 'sun', timezone: 'Not/AZone' }));
  assert.throws(() => profilePayload({ name: '名字', avatar: 'sun', timezone: '+08:00' }));
});
test('password validation catches missing current, length and confirmation without retaining values', () => {
  assert.ok(passwordErrors('', '12345678', '12345678').current);
  assert.ok(passwordErrors('old-secret', 'short', 'short').next);
  assert.ok(passwordErrors('old-secret', 'new-secret', 'different').confirm);
  assert.deepEqual(passwordErrors('old-secret', 'new-secret', 'new-secret'), {});
  assert.ok(!JSON.stringify(passwordErrors('old-secret', 'new-secret', 'different')).includes('old-secret'));
});
test('appearance restores validated local values and rejects malformed or unknown settings', async () => {
  assert.deepEqual(decodePreferences('{"mode":"dark","accent":"purple","password":"ignored"}'), { mode: 'dark', accent: 'purple' });
  assert.deepEqual(decodePreferences('{broken'), { mode: 'system', accent: 'blue' });
  assert.deepEqual(decodePreferences('{"mode":"unknown","accent":"red"}'), { mode: 'system', accent: 'blue' });
  assert.deepEqual(decodePreferences('{"mode":["dark"],"accent":["purple"]}'), { mode: 'system', accent: 'blue' });
  let stored = '{"mode":"dark","accent":"green"}';
  const controller = new AppearanceController({ read: async () => stored, write: async value => { stored = value; } });
  await controller.restore();
  assert.equal(controller.getSnapshot().preferences.mode, 'dark');
  assert.equal(await controller.save({ mode: 'light', accent: 'purple' }), true);
  const restored = new AppearanceController({ read: async () => stored, write: async () => {} });
  await restored.restore();
  assert.deepEqual(restored.getSnapshot().preferences, { mode: 'light', accent: 'purple' });
});
test('appearance storage failure keeps previous settings and never blocks account access', async () => {
  const controller = new AppearanceController({ read: async () => { throw new Error('storage denied'); }, write: async () => { throw new Error('storage full'); } });
  await controller.restore();
  assert.equal(controller.getSnapshot().ready, true);
  assert.equal(await controller.save({ mode: 'dark', accent: 'orange' }), false);
  assert.deepEqual(controller.getSnapshot().preferences, { mode: 'system', accent: 'blue' });
  assert.ok(controller.getSnapshot().error);
});

test('appearance writes are single-flight and restore cannot overwrite an in-flight user choice', async () => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  const writes: string[] = [];
  const controller = new AppearanceController({ read: async () => null, write: async value => { writes.push(value); await pending; } });
  await controller.restore();
  const saving = controller.save({ mode: 'dark', accent: 'purple' });
  assert.equal(await controller.save({ mode: 'light', accent: 'orange' }), false);
  await controller.restore();
  release(); assert.equal(await saving, true);
  assert.equal(writes.length, 1);
  assert.deepEqual(controller.getSnapshot().preferences, { mode: 'dark', accent: 'purple' });
});
