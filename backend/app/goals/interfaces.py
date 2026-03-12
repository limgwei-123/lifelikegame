from typing import Protocol
import uuid

class GoalServiceInterface(Protocol):
  def create_goal(self, payload, user_id: uuid.UUID):
    ...