from app.core.behaviors import ValidationIssue
from app.task_instances.commands import CompleteTaskInstanceCommand


class CompleteTaskInstanceCommandValidator:
  def validate(
      self,
      command: CompleteTaskInstanceCommand,
  ) -> list[ValidationIssue]:
    issues = []

    if command.task_instance_id <= 0:
      issues.append(ValidationIssue(
        field="task_instance_id",
        message="Task instance ID must be positive",
        code="positive",
      ))

    if not command.completion_level.strip():
      issues.append(ValidationIssue(
        field="completion_level",
        message="Completion level is required",
        code="required",
      ))
    elif len(command.completion_level) > 100:
      issues.append(ValidationIssue(
        field="completion_level",
        message="Completion level must not exceed 100 characters",
        code="max_length",
      ))

    return issues
