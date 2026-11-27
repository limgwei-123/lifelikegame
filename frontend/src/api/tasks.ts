import type { User } from './types';

export type ScheduleKind = 'once' | 'daily' | 'weekly' | 'monthly';
export interface Task {
  id: number; goal_id: number | null; title: string; description: string | null; is_active: boolean;
  scoring_scheme_id: number | null; scoring_scheme_json: Record<string, number> | null; is_scoring_scheme_locked: boolean;
}
export interface TaskInstance {
  id: number; user_id: string; task_id: number; task_schedule_id: number | null; date_instance: string;
  status: 'todo' | 'done' | 'skipped'; completion_level: string | null; score_awarded: number;
  scoring_snapshot_json: Record<string, number> | null; generated_reason: string | null;
  created_at: string; updated_at: string; deleted_at: string | null;
}
export interface ScheduleInput {
  schedule_type: ScheduleKind; schedule_value_json: { days?: number[]; day?: number };
  start_date: string; end_date: string | null;
}
export interface TaskSchedule extends Omit<ScheduleInput, 'start_date'> { id: number; task_id: number; start_date: string | null }
export interface Goal { id: number; title: string }
export interface ScoringScheme { id: number; title: string; levels_json: Record<string, number> }
export interface Progress {
  timezone: string; today: string; total_completed: number; completed_today: number; total_damage: number;
  current_streak: number; longest_streak: number; defeated_bosses: number;
  boss: { id: string; name: string; round: number; position: number; hp: number; max_hp: number };
  bosses: { id: string; name: string; max_hp: number; status: 'defeated' | 'current' | 'upcoming' }[];
}
export interface PointLedger { id: number; delta: number; entry_type: 'earn' | 'spend'; source_type: string; source_id: number }
export interface Completion {
  task_instance: TaskInstance; next_task_instance: TaskInstance | null; user: User;
  point_ledger: PointLedger | null; progress: Progress | null;
}
export interface CreatedTask { task: Task; schedule: TaskSchedule | null; task_instance: TaskInstance | null }
export interface CreateTaskInput {
  goal_id: number | null;
  task: { title: string; description: string | null; scoring_scheme_id: number | null };
  schedule: ScheduleInput;
}
