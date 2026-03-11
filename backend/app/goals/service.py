from app.goals import repository as goal_repository
from sqlalchemy.orm import Session
def create_goal(payload,user_id, db:Session):

  return goal_repository.create_goal(payload, user_id, db)