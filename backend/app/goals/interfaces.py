from typing import Protocol
import uuid
from app.goals.schemas import CreateGoalRequest,UpdateGoalRequest

class GoalServiceInterface(Protocol):
  def create_goal(self, user_id: uuid.UUID ,payload:CreateGoalRequest):
    ...

  def list_goals(self, user_id) -> list:
    ...

  def get_goal_by_id(self, id:int):
    ...

  def update_goal(self, goal_id, user_id, data:UpdateGoalRequest):
    ...

  def delete_goal(self, goal_id, user_id):
    ...