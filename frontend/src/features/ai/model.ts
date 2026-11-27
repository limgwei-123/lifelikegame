import type { ConversationMessage, DraftPlan, DraftTask, GeneratedResponse, SavedDraft } from '../../api/ai';

const object = (x: unknown): Record<string, unknown> => {
  if (!x || typeof x !== 'object' || Array.isArray(x)) throw new Error('计划格式不正确，请重新生成。');
  return x as Record<string, unknown>;
};
const title = (x: unknown) => {
  if (typeof x !== 'string' || !x.trim() || Array.from(x.trim()).length > 255) throw new Error('目标和任务名称需要 1–255 个字。');
  return x.trim();
};
export function draftPlan(value: unknown): DraftPlan {
  const plan = object(value);
  if (!Array.isArray(plan.tasks) || plan.tasks.length < 1 || plan.tasks.length > 3) throw new Error('计划需要保留 1–3 个任务。');
  return { goal_title: title(plan.goal_title), tasks: plan.tasks.map((value): DraftTask => {
    const task = object(value), rule = object(task.schedule_value_json);
    if (task.description != null && typeof task.description !== 'string') throw new Error('任务备注格式不正确。');
    if (task.scoring_scheme_id != null && (!Number.isSafeInteger(task.scoring_scheme_id) || Number(task.scoring_scheme_id) <= 0)) throw new Error('请选择有效的评分方案。');
    if (task.schedule_type !== 'daily' && task.schedule_type !== 'weekly') throw new Error('AI 计划支持每天或每周任务。');
    if (task.schedule_type === 'daily' && Object.keys(rule).length) throw new Error('每天任务不需要指定星期。');
    if (task.schedule_type === 'weekly' && (!Array.isArray(rule.days) || !rule.days.length || rule.days.some(d => !Number.isInteger(d) || d < 0 || d > 6) || Object.keys(rule).some(k => k !== 'days'))) throw new Error('请为每周任务至少选择一天。');
    return { title: title(task.title), description: typeof task.description === 'string' ? task.description.trim() || null : null,
      scoring_scheme_id: task.scoring_scheme_id == null ? null : Number(task.scoring_scheme_id), schedule_type: task.schedule_type,
      schedule_value_json: task.schedule_type === 'daily' ? {} : { days: [...new Set(rule.days as number[])].sort((a, b) => a - b) } };
  }) };
}
export function savedDraft(value: unknown): SavedDraft {
  const data = object(value);
  if (typeof data.draft_id !== 'string' || !/^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i.test(data.draft_id)) throw new Error('无法确认草稿，请重新生成。');
  return { draft_id: data.draft_id, plan: draftPlan(data.plan) };
}
export function generatedResponse(value: unknown): GeneratedResponse {
  const data = object(value);
  if (!['need_more_info', 'plan_ready'].includes(String(data.status)) || typeof data.message !== 'string'
    || !Array.isArray(data.questions) || data.questions.some(q => typeof q !== 'string') || !Array.isArray(data.conversation_history)
    || data.conversation_history.some(m => !m || !['user', 'assistant'].includes(m.role) || typeof m.content !== 'string')) throw new Error('AI 返回的计划格式不正确，请重试。');
  if (data.status === 'need_more_info' && (data.plan != null || data.draft_id != null)) throw new Error('AI 返回的追问格式不正确，请重试。');
  if (data.status === 'plan_ready' && data.questions.length) throw new Error('AI 返回的计划格式不正确，请重试。');
  const draft = data.status === 'plan_ready' ? savedDraft(data) : null;
  return { status: data.status as GeneratedResponse['status'], message: data.message, questions: data.questions.slice(0, 3),
    plan: draft?.plan ?? null, draft_id: draft?.draft_id ?? null, conversation_history: (data.conversation_history as ConversationMessage[]).slice(-6) };
}
