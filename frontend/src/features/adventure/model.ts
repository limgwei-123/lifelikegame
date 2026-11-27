import type { Progress } from '../../api/tasks';

export interface AdventureFeedback {
  instanceId: number; kind: 'hit' | 'defeat'; damage: 1; bossId: string; round: number;
  defeatedName: string | null; nextName: string;
}
// Feedback describes a confirmed server transition, never awards damage or
// computes a next boss. Ignore aggregate/background changes and stale replies.
export function completionFeedback(before: Progress, after: Progress, goalTask: boolean, instanceId: number): AdventureFeedback | null {
  if (!goalTask || after.total_damage - before.total_damage !== 1 || after.total_completed <= before.total_completed) return null;
  const defeated = after.defeated_bosses > before.defeated_bosses;
  return { instanceId, kind: defeated ? 'defeat' : 'hit', damage: 1, bossId: before.boss.id, round: before.boss.round,
    defeatedName: defeated ? before.boss.name : null, nextName: after.boss.name };
}
export function hpFraction(boss: { hp: number; max_hp: number }) {
  return Number.isFinite(boss.hp) && Number.isFinite(boss.max_hp) && boss.max_hp > 0
    ? Math.min(1, Math.max(0, boss.hp / boss.max_hp)) : 0;
}
