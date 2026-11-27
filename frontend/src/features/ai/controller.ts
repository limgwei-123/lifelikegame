import { ApiError, type AuthContext } from '../../api/client';
import type { ConfirmationOutcome, ConversationMessage, DraftPlan, SavedDraft } from '../../api/ai';
import type { SessionController } from '../../session/controller';
import { draftPlan, generatedResponse, savedDraft } from './model';

interface AIState {
  busy: boolean; messages: ConversationMessage[]; history: ConversationMessage[]; draft: SavedDraft | null;
  error: string | null; pendingId: string | null; outcome: 'confirmed' | 'consumed' | null;
}
const initial: AIState = { busy: false, messages: [], history: [], draft: null, error: null, pendingId: null, outcome: null };
export class AIController {
  private state: AIState = initial;
  private listeners = new Set<() => void>();
  private readonly context: AuthContext;
  private abort = new AbortController();
  private active = true;
  constructor(private readonly session: SessionController, private readonly confirmDraft: (id: string) => Promise<ConfirmationOutcome>) {
    const context = session.captureAuth(); if (!context) throw new Error('A signed-in session is required'); this.context = context;
  }
  getSnapshot = () => this.state;
  subscribe = (fn: () => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  private live = () => this.active && this.session.isCurrent(this.context);
  private publish(change: Partial<AIState>) { if (this.live()) { this.state = { ...this.state, ...change }; this.listeners.forEach(fn => fn()); } }
  activate = () => { this.active = true; if (this.abort.signal.aborted) this.abort = new AbortController(); };
  stop = () => { this.active = false; this.abort.abort(); };
  clearError = () => this.publish({ error: null });
  editPlan = (plan: DraftPlan) => {
    if (this.state.draft && !this.state.busy && !this.state.pendingId && !this.state.outcome) this.publish({ draft: { ...this.state.draft, plan }, error: null });
  };
  reset = () => { if (!this.state.busy && !this.state.pendingId) this.publish(initial); };
  private async request(path: string, body: unknown, timeoutMs?: number) {
    const value = await this.session.api.request(path, { method: 'POST', body, context: this.context, signal: this.abort.signal, timeoutMs });
    if (!this.live()) throw new ApiError(0, 'CANCELLED', ''); return value;
  }
  private async run(work: () => Promise<void>) {
    if (!this.live() || this.state.busy || this.state.outcome) return false;
    this.publish({ busy: true, error: null });
    try { await work(); return this.live(); }
    catch (error) { this.publish({ error: error instanceof Error ? error.message : '操作未完成，请重试。' }); return false; }
    finally { this.publish({ busy: false }); }
  }
  generate = (prompt: string) => {
    if (this.state.pendingId) return Promise.resolve(false);
    return this.run(async () => {
      const value = prompt.trim(); if (!value || Array.from(value).length > 4000) throw new Error('请输入 1–4000 个字的目标或补充说明。');
      // SDK allows three 20s attempts plus bounded backoff; leave time for
      // draft persistence and the response instead of aborting a valid retry.
      const result = generatedResponse(await this.request('/ai-planner/generate-plan', { user_prompt: value, conversation_history: this.state.history }, 75000));
      this.publish({ history: result.conversation_history, messages: [...this.state.messages, { role: 'user', content: value },
        { role: 'assistant', content: [result.message, ...result.questions.map((q, i) => `${i + 1}. ${q}`)].filter(Boolean).join('\n') }].slice(-12) as ConversationMessage[],
        draft: result.plan && result.draft_id ? { plan: result.plan, draft_id: result.draft_id } : null });
    });
  };
  confirm = (plan: DraftPlan) => {
    if (!this.state.draft || this.state.pendingId) return Promise.resolve(false);
    return this.run(async () => {
      const validated = draftPlan(plan);
      const saved = savedDraft(await this.request(`/ai-planner/drafts/${this.state.draft!.draft_id}/revisions`, validated));
      // Freeze this exact saved ID before the transaction; an uncertain retry
      // must never create a second revision and duplicate the same plan.
      this.publish({ draft: saved, pendingId: saved.draft_id });
      await this.finishConfirmation(saved.draft_id);
    }).then(ok => ok && !!this.state.outcome);
  };
  retryConfirmation = () => {
    if (!this.state.pendingId) return Promise.resolve(false);
    return this.run(() => this.finishConfirmation(this.state.pendingId!)).then(ok => ok && !!this.state.outcome);
  };
  private async finishConfirmation(id: string) {
    const result = await this.confirmDraft(id);
    if (!this.live()) return;
    if (result === 'confirmed' || result === 'consumed') this.publish({ outcome: result, pendingId: null });
    else if (result === 'invalid') this.publish({ pendingId: null, error: '草稿未能确认，请检查任务和评分方案后再试。' });
    else this.publish({ error: '尚未确认创建结果。可先查看首页，或重新核实；重新核实会使用同一份草稿。' });
  }
}
