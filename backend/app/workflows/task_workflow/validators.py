import uuid

from app.core.behaviors import ValidationIssue
from app.shared.enums import ScheduleType
from app.workflows.task_workflow.commands import ConfirmAiPlanCommand, CreateTaskWithScheduleCommand


class CreateTaskWithScheduleCommandValidator:
  def validate(
      self,
      command: CreateTaskWithScheduleCommand,
  ) -> list[ValidationIssue]:
    issues = []

    if command.goal_id <= 0:
      issues.append(ValidationIssue(
        field="goal_id",
        message="Goal ID must be positive",
        code="positive",
      ))

    if not command.payload.task.title.strip():
      issues.append(ValidationIssue(
        field="task.title",
        message="Task title is required",
        code="required",
      ))

    schedule = command.payload.schedule
    if schedule is None:
      return issues

    if schedule.schedule_type == ScheduleType.ONCE and schedule.start_date is None:
      issues.append(ValidationIssue(
        field="schedule.start_date",
        message="Start date is required for a one-time schedule",
        code="required",
      ))

    if (
        schedule.start_date is not None
        and schedule.end_date is not None
        and schedule.end_date < schedule.start_date
    ):
      issues.append(ValidationIssue(
        field="schedule.end_date",
        message="End date must not be before start date",
        code="date_range",
      ))

    return issues


class ConfirmAiPlanCommandValidator:
  def validate(self, command: ConfirmAiPlanCommand) -> list[ValidationIssue]:
    issues = []
    for field, label in (("user_id", "User ID"), ("draft_id", "Draft ID")):
      if not isinstance(getattr(command, field), uuid.UUID):
        issues.append(ValidationIssue(
          field=field, message=f"{label} must be a UUID", code="uuid",
        ))
    return issues
