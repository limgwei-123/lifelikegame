import type { GoalInput, RewardInput, SchemeInput, Redemption } from '../../api/management';
import { validDate } from '../tasks/dates';

function titleValue(title: string) {
  const value = title.trim();
  if (!value || Array.from(value).length > 255) throw new Error('名称需要 1–255 个字。');
  return value;
}
function optionalText(value: string) {
  const trimmed = value.trim();
  if (Array.from(trimmed).length > 255) throw new Error('进度文字最多 255 个字。');
  return trimmed || null;
}
function integer(value: string, negative: boolean) {
  const input = value.trim();
  if (!(negative ? /^-?\d+$/ : /^\d+$/).test(input)) throw new Error('请输入有效的整数分数。');
  const result = Number(input);
  if (!Number.isSafeInteger(result) || result > 2147483647 || result < (negative ? -2147483648 : 0)) throw new Error('分数超出可用范围。');
  return result;
}
export interface GoalForm { title: string; start: string; target: string; current: string; goal: string }
export function goalPayload(form: GoalForm): GoalInput {
  if (!validDate(form.start) || (form.target && !validDate(form.target))) throw new Error('请选择有效的日期。');
  return { title: titleValue(form.title), start_date: form.start, target_date: form.target || null,
    current_value: optionalText(form.current), target_value: optionalText(form.goal) };
}
export interface LevelForm { name: string; points: string }
export function schemePayload(title: string, rows: LevelForm[]): SchemeInput {
  if (!rows.length) throw new Error('请至少保留一个评分等级。');
  const names = new Set<string>();
  const entries = rows.map(row => {
    const name = row.name.trim();
    if (!name || Array.from(name).length > 100) throw new Error('等级名称需要 1–100 个字。');
    if (names.has(name)) throw new Error('等级名称不能重复。');
    names.add(name); return [name, integer(row.points, true)] as const;
  });
  return { title: titleValue(title), levels_json: Object.fromEntries(entries) };
}
export function rewardPayload(title: string, description: string, cost: string): RewardInput {
  return { title: titleValue(title), description: description.trim() || null, cost_points: integer(cost, false) };
}
export function redemptionTitle(entry: Pick<Redemption, 'reward_snapshot_json'>) {
  return entry.reward_snapshot_json?.title || '已删除的奖励';
}
