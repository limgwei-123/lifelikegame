import type { CreateTaskInput, ScheduleKind, Task, TaskInstance } from '../../api/tasks';
import { validDate } from './dates';

export interface TaskFormValue {
  title: string; description: string; goalId: number | null; schemeId: number | null;
  kind: ScheduleKind; start: string; end: string; days: number[]; monthDay: number;
}
export function buildTaskPayload(form: TaskFormValue): CreateTaskInput {
  if (!form.title.trim() || form.title.trim().length > 255) throw new Error('任务名称需要 1–255 个字符。');
  if (!validDate(form.start) || (form.end && !validDate(form.end))) throw new Error('请选择有效的日期。');
  if (form.kind !== 'once' && form.end && form.end < form.start) throw new Error('结束日期不能早于开始日期。');
  if (form.kind === 'weekly' && (!form.days.length || form.days.some(x => !Number.isInteger(x) || x < 0 || x > 6))) throw new Error('请至少选择一个重复日。');
  if (form.kind === 'monthly' && (!Number.isInteger(form.monthDay) || form.monthDay < 1 || form.monthDay > 31)) throw new Error('每月日期需要在 1–31 之间。');
  return {
    goal_id: form.goalId,
    task: { title: form.title.trim(), description: form.description.trim() || null, scoring_scheme_id: form.goalId === null ? null : form.schemeId },
    schedule: { schedule_type: form.kind, start_date: form.start, end_date: form.kind === 'once' ? null : form.end || null,
      schedule_value_json: form.kind === 'weekly' ? { days: [...new Set(form.days)].sort((a, b) => a - b) }
        : form.kind === 'monthly' ? { day: form.monthDay } : {} },
  };
}
export function completionLevels(task: Task, instance: TaskInstance): [string, number][] {
  return task.goal_id === null ? [] : Object.entries(instance.scoring_snapshot_json ?? {});
}
export function visibleInstances(selected: string, today: string, day: TaskInstance[], pending: TaskInstance[], tasks: Task[]) {
  const byTask = new Map(tasks.map(t => [t.id, t]));
  const dated = day.filter(i => i.date_instance === selected);
  const source = selected === today ? [...pending, ...dated.filter(i => i.status === 'done')] : dated;
  return [...new Map(source.filter(i => !i.deleted_at
    && (i.status === 'done' || (i.status === 'todo' && byTask.get(i.task_id)?.is_active))).map(i => [i.id, i])).values()]
    .sort((a, b) => Number(a.status === 'done') - Number(b.status === 'done') || a.date_instance.localeCompare(b.date_instance) || a.id - b.id);
}
