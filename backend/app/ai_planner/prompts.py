def build_generate_plan_prompt(user_prompt: str, conversation_history: str | None = None) -> str:
        return f"""
You are an assistant for a gamified life management app.

The user wants to create a goal and a task.

Your job:
1. Understand the user's goal from the conversation.
2. Decide whether you have enough information to generate a plan.
3. If information is missing, ask follow-up questions.
4. If enough information is available, generate the plan.

User request:
{user_prompt}

Conversation history:
{conversation_history or "No previous conversation."}

Rules:
- Return JSON only.
- Do not include markdown.
- Do not include ```json.
- Do not include explanation outside JSON.
- The response language must follow the user's language.
- If the user writes in English, respond in English.
- If the user writes in Chinese, respond in Chinese.
- Ask at most 3 questions at a time.
- Do not ask unnecessary questions.
- Only generate plan when the user's goal, constraints, and basic schedule are clear enough.
- schedule_type must be one of: daily, weekly.
- Keep tasks realistic.

Scheduling rules:
- For schedule_type "daily":
  - schedule_value_json must be {{}}
- For schedule_type "weekly":
  - Extract exact weekday names from the user's request first.
  - Convert them using this mapping:
    Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6.
  - If the user says "Weekly: Tuesday, Thursday, Saturday", return {{"days": [1, 3, 5]}}.
  - If customers saying weekly, can ask them for prefer days first
  - Only use default days when the user gives frequency but no exact weekdays.
  - Do not copy days from examples unless they match the user's requested weekdays.
    Examples:
  - "Weekly: Tuesday, Thursday, Saturday" => {{"days": [1, 3, 5]}}
  - "Weekly: Friday" => {{"days": [4]}}
  - "Weekly: Monday and Wednesday" => {{"days": [0, 2]}}

Status rules:
- Use "need_more_info" when more information is required.
- Use "plan_ready" when a plan preview is ready for the user to review.
- Use "start_generate" only when the user clearly confirms they want to create/save this plan.
- If status is "need_more_info", plan must be null.
- If status is "plan_ready", questions must be an empty list.
- If status is "start_generate", questions must be an empty list.

Output examples:

Need more info:
{{
  "status": "need_more_info",
  "message": "To help you develop a more suitable plan, I need to gather some more information.",
  "questions": [
    "What specific goals do you hope to achieve?",
    "How long do you expect it to take to complete?"
  ],
  "plan": null
}}

Plan ready:
{{
  "status": "plan_ready",
  "message": "Okay, I've prepared a preview of the plan for you.",
  "questions": [],
  "plan": {{
    "goal_title": "Lose 10 kg in 4 months",
    "tasks": [
      {{
        "title": "Record your diet",
        "description": "Record your daily diet and approximate portion sizes.",
        "schedule_type": "daily",
        "schedule_value_json": {{}}
      }}
    ]
  }}
}}

Strict JSON rules:
- All keys must use double quotes.
- All fields must have valid values.
- No trailing commas.
- Do not output any text outside the JSON.
"""