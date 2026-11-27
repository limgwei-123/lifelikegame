export interface ConversationMessage { role: 'user' | 'assistant'; content: string }
export interface DraftTask {
  title: string; description: string | null; scoring_scheme_id: number | null;
  schedule_type: 'daily' | 'weekly'; schedule_value_json: { days?: number[] };
}
export interface DraftPlan { goal_title: string; tasks: DraftTask[] }
export interface SavedDraft { draft_id: string; plan: DraftPlan }
export interface GeneratedResponse {
  status: 'need_more_info' | 'plan_ready'; message: string; questions: string[];
  plan: DraftPlan | null; draft_id: string | null; conversation_history: ConversationMessage[];
}
export type ConfirmationOutcome = 'confirmed' | 'consumed' | 'retry' | 'invalid';
