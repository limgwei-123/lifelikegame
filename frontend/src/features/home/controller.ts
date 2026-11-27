import { ApiError, type AuthContext } from '../../api/client';
import type { Completion, CreatedTask, CreateTaskInput, Progress, ScheduleInput, ScoringScheme, Task, TaskInstance, TaskSchedule } from '../../api/tasks';
import type { GoalDetails, GoalInput, SchemeInput, RewardInput, Reward, Redemption, LedgerEntry, ManagementData, RedeemedReward } from '../../api/management';
import type { User } from '../../api/types';
import { isUser } from '../../api/types';
import type { ProfileInput } from '../account/model';
import type { SessionController } from '../../session/controller';
import { validDate } from '../tasks/dates';
import { completionFeedback, type AdventureFeedback } from '../adventure/model';

export interface HomeData {
  date: string;
  progress: Progress; tasks: Task[]; schedules: TaskSchedule[]; goals: GoalDetails[]; schemes: ScoringScheme[];
  day: TaskInstance[]; pending: TaskInstance[]; month: TaskInstance[];
}
export interface HomeSnapshot {
  selectedDate: string | null; data: HomeData | null; loading: boolean; busy: boolean;
  error: string | null; notice: string | null; lastCompletion: Completion | null;
  feedback: AdventureFeedback | null;
  management: ManagementData | null;
}
const initial: HomeSnapshot = { selectedDate: null, data: null, loading: true, busy: false, error: null, notice: null, lastCompletion: null, feedback: null, management: null };
const upsert = <T extends { id: number }>(items: T[], item: T) => [...items.filter(x => x.id !== item.id), item];

// One serialized queue owns reads and writes. It is scoped to a single login,
// so late responses and queued writes cannot use a replacement account's token.
export class HomeController {
  private state: HomeSnapshot = initial;
  private listeners = new Set<() => void>();
  private queue: Promise<unknown> = Promise.resolve();
  private readonly context: AuthContext;
  private abort = new AbortController();
  private active = true;
  private epoch = 0;
  private viewVersion = 0;
  private repairedDay: string | null = null;
  private completed = new Set<number>();
  private redeemed = new Set<number>();
  private managementRequested = false;
  constructor(private readonly session: SessionController) {
    const context = session.captureAuth();
    if (!context) throw new Error('A signed-in session is required');
    this.context = context;
  }
  getSnapshot = () => this.state;
  subscribe = (fn: () => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  private live() { return this.active && this.session.isCurrent(this.context); }
  private publish(change: Partial<HomeSnapshot>) {
    if (!this.live()) return;
    this.state = { ...this.state, ...change }; this.listeners.forEach(fn => fn());
  }
  private async request<T>(path: string, body?: unknown, method?: string): Promise<T> {
    if (!this.live()) throw new ApiError(0, 'CANCELLED', '');
    const signal = this.abort.signal;
    const value = await this.session.api.request<T>(path, { context: this.context, signal,
      ...(body === undefined ? {} : { method: method ?? 'POST', body }) });
    if (signal.aborted || !this.live()) throw new ApiError(0, 'CANCELLED', '');
    return value;
  }
  private serial<T>(work: () => Promise<T>, fallback: T) {
    const epoch = this.epoch;
    const next = this.queue.catch(() => {}).then(() => epoch === this.epoch && this.live() ? work() : fallback);
    this.queue = next; return next;
  }
  private error(error: unknown) { return error instanceof Error ? error.message : '操作未能完成，请重试。'; }
  activate = () => { this.active = true; if (this.abort.signal.aborted) this.abort = new AbortController(); };
  stop = () => { this.active = false; this.epoch++; this.abort.abort(); };
  clearNotice = () => this.publish({ notice: null });
  clearMessages = () => this.publish({ notice: null, error: null });
  clearFeedback = (instanceId: number) => {
    if (this.state.feedback?.instanceId === instanceId) this.publish({ feedback: null });
  };

  selectDate = (value: string) => {
    if (!validDate(value)) return Promise.resolve();
    this.publish({ selectedDate: value, notice: null }); return this.refresh();
  };
  refreshManagement = () => { this.managementRequested = true; return this.refresh(false, true); };
  refresh = (repair = false, management = this.managementRequested): Promise<void> => {
    const version = ++this.viewVersion;
    this.publish({ loading: true, error: null });
    return this.serial(async () => {
      if (version !== this.viewVersion) return;
      try { await this.load(version, repair); if (management) await this.loadManagement(version); }
      catch (error) { if (version === this.viewVersion) this.publish({ error: this.error(error) }); }
      finally { if (version === this.viewVersion) this.publish({ loading: false }); }
    }, undefined);
  };
  private async load(version: number, repair: boolean) {
    const before = this.state.data?.progress;
    const progress = await this.request<Progress>('/progress');
    if (!validDate(progress.today)) throw new ApiError(502, 'INVALID_RESPONSE', '无法读取日期，请重试。');
    if (repair && this.repairedDay !== `${progress.timezone}:${progress.today}`) {
      await this.request('/tasks_instances/generate', { date_instance: progress.today });
      this.repairedDay = `${progress.timezone}:${progress.today}`;
    }
    const selected = !this.state.selectedDate || (before && before.today !== progress.today && this.state.selectedDate === before.today)
      ? progress.today : this.state.selectedDate;
    const [tasks, schedules, goals, schemes, user, day, pending, month] = await Promise.all([
      this.request<Task[]>('/tasks'), this.request<TaskSchedule[]>('/task_schedules'), this.request<GoalDetails[]>('/goals'),
      this.request<ScoringScheme[]>('/scoring_schemes'), this.request<User>('/users/me'),
      this.request<TaskInstance[]>(`/task_instances?date=${selected}`),
      this.request<TaskInstance[]>(`/task_instances/pending?date=${progress.today}`),
      this.request<TaskInstance[]>(`/task_instances/month?year=${Number(selected.slice(0, 4))}&month=${Number(selected.slice(5, 7))}`),
    ]);
    if (version !== this.viewVersion) return;
    this.session.updateUser(user, this.context);
    this.publish({ selectedDate: selected, data: { date: selected, progress, tasks, schedules, goals, schemes, day, pending, month } });
  }
  private async loadManagement(version: number) {
    const [rewards, redemptions, ledger, points] = await Promise.all([
      this.request<Reward[]>('/rewards'), this.request<Redemption[]>('/redemptions'),
      this.request<LedgerEntry[]>('/point_ledgers'), this.request<{ balance: number }>('/point_ledgers/balance'),
    ]);
    if (version !== this.viewVersion) return;
    if (!Number.isSafeInteger(points.balance)) throw new ApiError(502, 'INVALID_RESPONSE', '无法确认积分余额，请刷新重试。');
    const user = this.session.getSnapshot().user;
    if (user) this.session.updateUser({ ...user, current_value: points.balance }, this.context);
    this.publish({ management: { rewards, redemptions, ledger, balance: points.balance } });
  }
  private mutate(work: () => Promise<void>, success: string | null, reload = true): Promise<boolean> {
    if (!this.live() || this.state.busy || this.state.loading) return Promise.resolve(false);
    this.publish({ busy: true, error: null, notice: null });
    return this.serial(async () => {
      try {
        await work();
        if (!this.live()) return false;
        this.publish({ notice: success });
        if (reload) {
          const version = ++this.viewVersion;
          try { await this.load(version, false); if (this.state.management) await this.loadManagement(version); }
          catch { this.publish({ error: '操作已保存，但列表刷新失败。请刷新查看。' }); }
          finally { if (version === this.viewVersion) this.publish({ loading: false }); }
        }
        return true;
      } catch (error) {
        this.publish({ error: this.error(error) }); return false;
      } finally { this.publish({ busy: false }); }
    }, false);
  }
  saveGoal = (input: GoalInput, id?: number) => this.mutate(async () => {
    const saved = await this.request<GoalDetails>(id === undefined ? '/goals' : `/goals/${id}`, input);
    if (this.state.data) this.publish({ data: { ...this.state.data, goals: upsert(this.state.data.goals, saved) } });
  }, id === undefined ? '目标已添加' : '目标已更新');
  deleteGoal = (id: number) => this.mutate(async () => {
    await this.request(`/goals/${id}/delete`, {});
    if (this.state.data) this.publish({ data: { ...this.state.data, goals: this.state.data.goals.filter(g => g.id !== id), tasks: this.state.data.tasks.filter(t => t.goal_id !== id) } });
  }, '目标已删除');
  saveScheme = (input: SchemeInput, id?: number) => this.mutate(async () => {
    const saved = await this.request<ScoringScheme>(id === undefined ? '/scoring_schemes' : `/scoring_schemes/${id}`, input);
    if (this.state.data) this.publish({ data: { ...this.state.data, schemes: upsert(this.state.data.schemes, saved) } });
  }, id === undefined ? '评分方案已添加' : '评分方案已更新');
  deleteScheme = (id: number) => this.mutate(async () => {
    await this.request(`/scoring_schemes/${id}/delete`, {});
    if (this.state.data) this.publish({ data: { ...this.state.data, schemes: this.state.data.schemes.filter(s => s.id !== id) } });
  }, '评分方案已删除');
  saveReward = (input: RewardInput, id?: number) => this.mutate(async () => {
    const saved = await this.request<Reward>(id === undefined ? '/rewards' : `/rewards/${id}`, input);
    if (this.state.management) this.publish({ management: { ...this.state.management, rewards: upsert(this.state.management.rewards, saved) } });
  }, id === undefined ? '奖励已添加' : '奖励已更新');
  deleteReward = (id: number) => this.mutate(async () => {
    await this.request(`/rewards/${id}/delete`, {});
    if (this.state.management) this.publish({ management: { ...this.state.management, rewards: this.state.management.rewards.filter(r => r.id !== id) } });
  }, '奖励已删除');
  redeemReward = (reward: Reward): Promise<boolean> => {
    if (reward.status !== 'available' || this.redeemed.has(reward.id)) return Promise.resolve(false);
    return this.mutate(async () => {
      // Recheck the offer before charging; an old sheet must not silently accept
      // another session's changed price or title. The server owns the transaction.
      const rewards = await this.request<Reward[]>('/rewards');
      if (this.state.management) this.publish({ management: { ...this.state.management, rewards } });
      const latest = rewards.find(item => item.id === reward.id);
      if (!latest || latest.status !== 'available' || latest.cost_points !== reward.cost_points || latest.title !== reward.title) {
        throw new ApiError(409, 'OFFER_CHANGED', '奖励已变更，请关闭并重新选择后确认。');
      }
      const result = await this.request<RedeemedReward>(`/workflows/rewards/${reward.id}/redeem`, {});
      if (result.reward_id !== reward.id || !Number.isSafeInteger(result.remaining_points) || result.remaining_points < 0 || !Number.isSafeInteger(result.redemption_id)) {
        throw new ApiError(502, 'INVALID_RESPONSE', '无法确认兑换结果，请刷新后查看。');
      }
      this.redeemed.add(reward.id);
      const user = this.session.getSnapshot().user;
      if (user) this.session.updateUser({ ...user, current_value: result.remaining_points }, this.context);
      if (this.state.management) this.publish({ management: { ...this.state.management, balance: result.remaining_points,
        rewards: upsert(this.state.management.rewards, { ...reward, status: 'redeemed' }) } });
    }, '奖励已兑换');
  };
  saveProfile = (input: ProfileInput) => this.mutate(async () => {
    const previous = this.session.getSnapshot().user;
    const updated = await this.request<User>('/users/me', input, 'PATCH');
    if (!isUser(updated) || updated.id !== previous?.id) throw new ApiError(502, 'INVALID_RESPONSE', '无法确认账户资料，请刷新后重试。');
    this.session.updateUser(updated, this.context);
    if (previous.timezone !== updated.timezone) await this.repairAfterSave();
  }, '个人资料已保存');
  changePassword = (current: string, next: string): Promise<boolean> => {
    if (!this.live() || this.state.busy || this.state.loading) return Promise.resolve(false);
    this.publish({ busy: true, error: null, notice: null });
    return this.serial(async () => {
      try {
        // Passwords exist only in this request closure, never in a snapshot/store.
        await this.request('/auth/change-password', { current_password: current, new_password: next });
        await this.session.logout('密码已更新，请重新登录。');
        return this.session.getSnapshot().status === 'signedOut';
      } catch (error) { this.publish({ error: this.error(error) }); return false; }
      finally { this.publish({ busy: false }); }
    }, false);
  };
  create = (input: CreateTaskInput) => this.mutate(async () => {
    const created = await this.request<CreatedTask>('/workflows/tasks', input);
    if (this.state.data) this.publish({ data: { ...this.state.data,
      tasks: upsert(this.state.data.tasks, created.task),
      schedules: created.schedule ? upsert(this.state.data.schedules, created.schedule) : this.state.data.schedules } });
  }, '任务已添加');
  editTask = (id: number, title: string, description: string) => this.mutate(async () => {
    const task = await this.request<Task>(`/tasks/${id}`, { title: title.trim(), description: description.trim() || null });
    if (this.state.data) this.publish({ data: { ...this.state.data, tasks: upsert(this.state.data.tasks, task) } });
  }, '任务已更新');
  updateSchedule = (id: number, schedule: ScheduleInput) => this.mutate(async () => {
    const updated = await this.request<TaskSchedule>(`/task_schedules/${id}`, schedule);
    if (this.state.data) this.publish({ data: { ...this.state.data, schedules: upsert(this.state.data.schedules, updated) } });
    await this.repairAfterSave();
  }, '重复设置已更新；当前任务保留原日期');
  private async repairAfterSave() {
    this.repairedDay = null;
    try {
      const progress = await this.request<Progress>('/progress');
      await this.request('/tasks_instances/generate', { date_instance: progress.today });
      this.repairedDay = `${progress.timezone}:${progress.today}`;
    } catch { this.publish({ error: '修改已保存，当前记录尚未刷新，请刷新重试。' }); }
  }
  toggleTask = (task: Task) => this.mutate(async () => {
    const updated = await this.request<Task>(`/tasks/${task.id}`, { is_active: !task.is_active });
    if (this.state.data) this.publish({ data: { ...this.state.data, tasks: upsert(this.state.data.tasks, updated) } });
    if (!task.is_active) {
      // Restoring an unscheduled current occurrence is an explicit write action.
      // Generation is idempotent server-side and never targets the viewed date.
      await this.repairAfterSave();
    }
  }, task.is_active ? '任务已暂停' : '任务已恢复');
  deleteTask = (id: number) => this.mutate(async () => {
    await this.request(`/tasks/${id}/delete`, {});
    if (this.state.data) this.publish({ data: { ...this.state.data, tasks: this.state.data.tasks.filter(t => t.id !== id) } });
  }, '任务已删除');
  complete = (instance: TaskInstance, level?: string): Promise<boolean> => {
    const data = this.state.data;
    if (!data || this.completed.has(instance.id) || instance.status !== 'todo' || instance.date_instance > data.progress.today) return Promise.resolve(false);
    return this.mutate(async () => {
      const result = await this.request<Completion>(`/task_instances/${instance.id}/complete`, level === undefined ? {} : { completion_level: level });
      this.completed.add(result.task_instance.id);
      const current = this.state.data!;
      this.session.updateUser(result.user, this.context);
      const merge = (rows: TaskInstance[], predicate: (i: TaskInstance) => boolean) => {
        let updated = rows.filter(i => i.id !== result.task_instance.id && i.id !== result.next_task_instance?.id);
        for (const item of [result.task_instance, result.next_task_instance]) if (item && predicate(item)) updated = upsert(updated, item);
        return updated;
      };
      const progress = result.progress ?? await this.request<Progress>('/progress');
      const goalTask = current.tasks.find(t => t.id === instance.task_id)?.goal_id != null;
      this.publish({ lastCompletion: result, feedback: completionFeedback(current.progress, progress, goalTask, result.task_instance.id), data: { ...current, progress,
        day: merge(current.day, i => i.date_instance === this.state.selectedDate),
        month: merge(current.month, i => i.date_instance.slice(0, 7) === this.state.selectedDate?.slice(0, 7)),
        pending: merge(current.pending, i => i.status === 'todo' && i.date_instance <= progress.today) } });
    }, data.tasks.find(t => t.id === instance.task_id)?.goal_id != null ? null : '已完成', false);
  };
}
