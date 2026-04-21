
from enum import StrEnum
import enum

class TaskInstanceStatus(StrEnum):
  TODO = "todo"
  DONE = "done"
  SKIPPED = "skipped"

class EntryType(StrEnum):
  EARN = "earn"
  SPEND = "spend"

class ScheduleType(str, enum.Enum):
  DAILY = "daily"
  WEEKLY = "weekly"
  MONTHLY = "monthly"
  ONCE = "once"

class RewardStatus(StrEnum):
  AVAILABLE = "available"
  REDEEMED = "redeemed"
