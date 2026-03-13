from typing import Protocol
import uuid

class GoalServiceInterface(Protocol):
  def create_goal(self, user_id: uuid.UUID ,payload):
    ...

  def list_goals(self, user_id) -> list:
    ...

  def get_goal_by_id(self, id:int):
    ...

  def update_goal(self, goal_id, user_id, data):
    ...

  def delete_goal(self, goal_id, user_id):
    ...