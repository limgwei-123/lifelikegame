import uuid

from app.core.behaviors import ValidationIssue
from app.workflows.redemption_workflow.commands import RedeemRewardCommand


class RedeemRewardCommandValidator:
  def validate(self, command: RedeemRewardCommand) -> list[ValidationIssue]:
    issues = []

    if type(command.reward_id) is not int:
      issues.append(ValidationIssue(
        field="reward_id", message="Reward ID must be an integer", code="integer",
      ))
    elif command.reward_id <= 0:
      issues.append(ValidationIssue(
        field="reward_id", message="Reward ID must be positive", code="positive",
      ))

    if not isinstance(command.user_id, uuid.UUID):
      issues.append(ValidationIssue(
        field="user_id", message="User ID must be a UUID", code="uuid",
      ))

    return issues
