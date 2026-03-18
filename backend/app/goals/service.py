from app.goals.repository import GoalRepository
from app.goals.schemas import CreateGoalRequest,UpdateGoalRequest
from app.errors.exception import NotFoundError

class GoalService:
  def __init__(self, goal_repo: GoalRepository):
    self.goal_repo = goal_repo

  def create_goal(self,user_id, payload:CreateGoalRequest):
    data = payload.model_dump()
    data['user_id'] = user_id
    return self.goal_repo.create_goal(data)

  def list_goals(self, user_id):
    return self.goal_repo.list_goals(user_id)

  def get_goal_by_id(self, goal_id, user_id):
    return self._get_owned_goal_or_raise(goal_id, user_id)


  def update_goal(self, goal_id, user_id, data: UpdateGoalRequest):
    goal = self._get_owned_goal_or_raise(goal_id, user_id)

    return self.goal_repo.update_goal(
      goal,
      data.model_dump(exclude_unset=True)
    )

  def delete_goal(self, goal_id, user_id):
    goal = self._get_owned_goal_or_raise(goal_id, user_id)

    self.goal_repo.delete_goal(goal)


  def _get_owned_goal_or_raise(self , goal_id, user_id):
    goal = self.goal_repo.get_by_goal_id_and_user_id(goal_id, user_id)
    if not goal:
      raise NotFoundError("Goal not found")
    return goal