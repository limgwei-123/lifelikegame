import assert from 'node:assert/strict';
import { test } from 'node:test';
import { goalPayload, schemePayload, rewardPayload, redemptionTitle } from '../src/features/management/model.ts';

test('goal fields preserve optional progress text and clear optional dates explicitly', () => {
  assert.deepEqual(goalPayload({ title: '  每周运动 ', start: '2026-11-27', target: '', current: '1 次', goal: '3 次 / 周' }),
    { title: '每周运动', start_date: '2026-11-27', target_date: null, current_value: '1 次', target_value: '3 次 / 周' });
  assert.throws(() => goalPayload({ title: ' ', start: '2026-11-27', target: '', current: '', goal: '' }));
  assert.throws(() => goalPayload({ title: '目标', start: '2026-02-30', target: '', current: '', goal: '' }));
});
test('scheme levels keep zero/negative integers, reject duplicates and preserve safe JSON keys', () => {
  const result = schemePayload(' 我的方案 ', [{ name: ' 完成 ', points: '3' }, { name: '休息', points: '0' }, { name: '调整', points: '-1' }]);
  assert.deepEqual(result, { title: '我的方案', levels_json: { '完成': 3, '休息': 0, '调整': -1 } });
  assert.throws(() => schemePayload('方案', [{ name: '完成', points: '1' }, { name: ' 完成 ', points: '2' }]));
  assert.throws(() => schemePayload('方案', []));
  assert.throws(() => schemePayload('方案', [{ name: 'a'.repeat(101), points: '1' }]));
  assert.throws(() => schemePayload('方案', [{ name: '完成', points: '1.5' }]));
  const special = schemePayload('方案', [{ name: '__proto__', points: '1' }]);
  assert.equal(JSON.parse(JSON.stringify(special.levels_json)).__proto__, 1);
});
test('reward cost accepts zero and rejects negative, decimal and oversized values', () => {
  assert.deepEqual(rewardPayload(' 看电影 ', '  放松 ', '0'), { title: '看电影', description: '放松', cost_points: 0 });
  for (const value of ['-1', '1.5', '', '9007199254740992']) assert.throws(() => rewardPayload('奖励', '', value));
});
test('redemption history uses its saved title even after the reward was renamed or deleted', () => {
  assert.equal(redemptionTitle({ reward_snapshot_json: { title: '原来的奖励', cost_points: 3, description: null } }), '原来的奖励');
  assert.equal(redemptionTitle({ reward_snapshot_json: null }), '已删除的奖励');
});
