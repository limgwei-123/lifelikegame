from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.goals.models import Goal

def create_goal(payload,user_id,db: Session):
  goal_data = payload.model_dump()
  goal_data['user_id'] = user_id
  goal = Goal(**goal_data)
  db.add(goal)
  db.commit()
  db.refresh(goal)
  return goal