1) 用户与目标
users (账号)
- id
- email
- display_name
- password
- timezone
- created_at
- deleted_at

goals (目标)
- id
- user_id
- title
- category(fitness / study / sleep / finance…)
- status (active/deleted/done)
- start_date
- target_date (optional)
- current target value
- others (text form, optional, for user to key in what they want)
- created_at
- deleted_at

2) 计划 （先跳）
(当顾客不满意可以manual adjust或者告诉我们什么不满意，我们再重新生成一个新的，不需要plan version) (一个计划会有可以有个tasks)
plans(针对某个 goal 的“可执行方案)
- id
- goal_id
- name
- status (draft/active/archived)
- active_from
- active_to (optional)
- created_at
- deleted_at

plan_revisions (计划的“修改历史/版本记录”)（先跳）
- id
- plan_id
- revision_no (1,2,3)
- source (agent_generated/user_edited)
- summary (改了什么)
- payload_json (这次生成的 tasks/schedules/参数快照)
- created_at

3) 任务定义（模板）与排程（可扩展到任何频率）
tasks (任务模板（要做什么）)
- id
- plan_id(先跳)
- goal_id
- title
- scoring_scheme_id( get_from_scope_id)
- description (optional)
- is_active
- created_at
- deleted_at

task_schedules (这个任务“什么时候做”（排程规则）)
- id
- task_id
- schedule_type (daily / weekly_n / specific_days / monthly / once)
- schedule_value_json
 - weekly_n: { "n": 3, "week_start": "mon" }
 - specific_days: { "days": ["mon","wed","fri"] }
 - monthly: { "day_of_month": 1 }
 - once: { "date": "2026-03-10" }
- start_date (optional)
- end_date (optional)
- priority (optional)
- created_at
- deleted_at

4) 每日任务实例（今天要做什么）与打卡

task_instances (某一天实际“应该出现”的任务条目（今日待办）)
- id
- UNIQUE(task_id, date)
- task_id
- date (YYYY-MM-DD)
- status (todo/done/skipped)
- generated_reason (例如：weekly_quota_remaining)
- created_at
- deleted_at

checkins (用户“打卡行为记录”)
- id
- user_id
- task_instance_id
- completion level(text)
- score_awarded (point)
- scoring_snapshot_json {
  "perfect": 3,
  "normal": 2,
  "minimal": 1,
  "none": 0
}
- note(text, optional)
- created_at
- updated_at

5) 积分规则可自定义
scoring_schemes (一套“积分规则方案”，可给用户/任务套用)
- id
- user_id
- title (默认：3/2/1)
- levels_json 例：{"perfect":3,"normal":2,"minimal":1,"none":0}
- created_at
- deleted_at

points_ledger (积分账本（加分/扣分的唯一真相来源）)
UNIQUE(reason_type, reason_ref_id)
- id
- user_id
- date_time
- delta (+3 / -20)
- reason_type (checkin / redeem)
- reason_ref_id(关联 checkin 或 redemption)
- balance_after (optional)
-created_at

6) 奖励与兑换（用户自定义
rewards (用户自定义的“奖励清单”)
- id
- user_id
- title ("例如吃火锅")
- cost_points
- description (optional)
- is_active
- created_at

redemptions (一次“兑换记录")
- id
- reward_id
- user_id
- redemeed_at
- cost_points (冗余保存，防止 reward 后改价影响历史)
- created_at

7) RAG/Agent 的可追溯性
knowledge_sources (RAG 的知识来源文档清单)
(optional，这个部分主要是为了extract data，例如减肥资料这些来生成plan)
- id
- name
- type (md/pdf/web)
- path/url
- created_at

