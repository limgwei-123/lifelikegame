from typing import Protocol
import uuid

class GoalServiceInterface(Protocol):
  def create_goal(self, payload, user_id: uuid.UUID):
    ...

  def get_goal_by_id(self, id:int):
    ...