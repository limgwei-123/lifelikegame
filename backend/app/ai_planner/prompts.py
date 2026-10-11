from app.ai_planner.providers.base import ConversationMessage, MAX_GENERATED_TASKS

MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_MESSAGE_CHARS = 1000
MAX_HISTORY_CHARS = 4000


def _format_history(history: list[ConversationMessage] | None) -> str:
    if not history:
        return "No previous conversation."

    segments = []
    remaining = MAX_HISTORY_CHARS
    # Reserve the budget for newest messages, then restore chronological order.
    for message in reversed(history[-MAX_HISTORY_MESSAGES:]):
        prefix = f"{message.role}: "
        separator_size = 1 if segments else 0
        available = min(MAX_HISTORY_MESSAGE_CHARS, remaining - len(prefix) - separator_size)
        if available <= 0:
            break
        content = message.content
        if len(content) > available:
            marker = " [truncated]"
            if available < len(marker):
                break
            content = content[:available - len(marker)] + marker
        segment = prefix + content
        segments.append(segment)
        remaining -= len(segment) + separator_size
    return "\n".join(reversed(segments))


def build_generate_plan_prompt(
    user_prompt: str, conversation_history: list[ConversationMessage] | None = None,
) -> str:
    return f"""You plan goals and practical tasks for a gamified life management app.
Respond in the user's language and follow the supplied response schema.

Planning rules:
- Use the conversation to understand the goal, constraints, and basic schedule.
- If essential information is missing, use need_more_info, set plan to null,
  and ask at most 3 focused questions. Do not ask for information already given.
- Otherwise, use plan_ready and provide a goal with realistic, actionable tasks
  for the user to review. Set questions to an empty list.
- Generate 1 to {MAX_GENERATED_TASKS} tasks, never more, even if the user asks for more.
  Use fewer tasks for simple goals; do not add filler tasks to reach the limit.
- Respect the user's stated preferences and constraints.
- History may be truncated. Ask if essential details are no longer available.

Scheduling rules:
- For daily tasks, set schedule_value_json to {{}}.
- For weekly tasks, preserve the user's exact weekdays using this mapping:
  Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6.
- Put weekday numbers in schedule_value_json.days. For example, Friday is [4].
  Do not copy the example unless it matches the user's request.
- If weekdays are essential but unclear, ask for them. Only use the default
  [1, 3, 5] when the user gives a frequency without exact weekday preferences.

User request:
{user_prompt}

Conversation history:
{_format_history(conversation_history)}
"""
