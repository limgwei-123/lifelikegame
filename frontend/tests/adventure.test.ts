import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { Progress } from '../src/api/tasks.ts';
import { completionFeedback, hpFraction } from '../src/features/adventure/model.ts';

function progress(damage = 0): Progress {
  return { today: '2026-11-27', timezone: 'Asia/Kuala_Lumpur', total_completed: damage, completed_today: damage,
    total_damage: damage, current_streak: damage ? 1 : 0, longest_streak: damage ? 1 : 0, defeated_bosses: 0,
    boss: { id: 'slime', name: '软糖史莱姆', round: 1, position: 1, hp: 2 - damage, max_hp: 2 }, bosses: [] };
}
test('a goal completion reports one hit; ordinary todos never fabricate damage', () => {
  const before = progress(), after = progress(1);
  assert.equal(completionFeedback(before, after, false, 10), null);
  const event = completionFeedback(before, after, true, 10)!;
  assert.equal(event.kind, 'hit');
  assert.equal(event.damage, 1);
  assert.equal(event.instanceId, 10);
  assert.equal(event.bossId, 'slime');
  assert.equal(completionFeedback(after, after, true, 10), null);
  assert.equal(completionFeedback(after, before, true, 10), null);
});
test('boss and round transitions follow server values without subtracting HP locally', () => {
  const before = progress(1);
  const after = { ...progress(2), defeated_bosses: 1, boss: { id: 'cloud', name: '困困云怪', round: 1, position: 2, hp: 4, max_hp: 4 } };
  const event = completionFeedback(before, after, true, 11)!;
  assert.equal(event.kind, 'defeat');
  assert.equal(event.defeatedName, '软糖史莱姆');
  assert.equal(event.nextName, '困困云怪');
  const dragon = { ...progress(74), defeated_bosses: 5, boss: { id: 'dragon', name: '皇冠小龙', round: 1, position: 6, hp: 1, max_hp: 30 } };
  const round2 = { ...progress(75), defeated_bosses: 6, boss: { id: 'slime', name: '软糖史莱姆', round: 2, position: 1, hp: 32, max_hp: 32 } };
  assert.equal(completionFeedback(dragon, round2, true, 12)?.kind, 'defeat');
  assert.equal(hpFraction(round2.boss), 1);
  assert.equal(hpFraction({ hp: 1, max_hp: 32 }), 1 / 32);
});
test('background multi-completion changes do not masquerade as one local attack', () => {
  assert.equal(completionFeedback(progress(), progress(2), true, 13), null);
  assert.equal(hpFraction({ hp: 9, max_hp: 4 }), 1);
  assert.equal(hpFraction({ hp: -1, max_hp: 4 }), 0);
  assert.equal(hpFraction({ hp: 1, max_hp: 0 }), 0);
});
