import type { Goal, ScoringScheme } from './tasks';

export interface GoalInput { title: string; start_date: string; target_date: string | null; current_value: string | null; target_value: string | null }
export interface GoalDetails extends GoalInput, Goal { user_id: string }
export interface SchemeInput { title: string; levels_json: Record<string, number> }
export interface RewardInput { title: string; description: string | null; cost_points: number }
export interface Reward extends RewardInput { id: number; user_id: string; status: 'available' | 'redeemed'; created_at: string; updated_at: string }
export interface Redemption {
  id: number; user_id: string; reward_id: number; cost_points: number; created_at: string;
  reward_snapshot_json: { title: string; description: string | null; cost_points: number } | null;
}
export interface LedgerEntry {
  id: number; user_id: string; event_at: string; delta: number; entry_type: string;
  source_type: string | null; source_id: number | null; description: string | null; created_at: string;
}
export interface RedeemedReward {
  redemption_id: number; reward_id: number; reward_title: string; cost_points: number; remaining_points: number; redeemed_at: string;
}
export interface ManagementData { rewards: Reward[]; redemptions: Redemption[]; ledger: LedgerEntry[]; balance: number }
export type ManagementKind = 'goals' | 'scoring' | 'rewards' | 'points';
export type EditableItem = { kind: 'goals'; value?: GoalDetails } | { kind: 'scoring'; value?: ScoringScheme } | { kind: 'rewards'; value?: Reward };
