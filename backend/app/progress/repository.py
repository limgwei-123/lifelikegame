from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.progress.models import TaskCompletion


class ProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_completion(self, user_id, task_instance_id):
        return self.db.scalar(select(TaskCompletion).where(
            TaskCompletion.user_id == user_id,
            TaskCompletion.task_instance_id == task_instance_id,
        ))

    def add(self, record: TaskCompletion) -> TaskCompletion:
        self.db.add(record)
        self.db.flush()
        return record

    def daily_counts(self, user_id):
        # One statement keeps completed counts, damage and local activity dates
        # on the same database snapshot, including during concurrent completions.
        return self.db.execute(select(
            TaskCompletion.completed_local_date,
            func.count(TaskCompletion.id).label('completed_count'),
            func.sum(case((TaskCompletion.is_goal_task.is_(True), 1), else_=0)).label('damage'),
        ).where(TaskCompletion.user_id == user_id).group_by(
            TaskCompletion.completed_local_date,
        ).order_by(TaskCompletion.completed_local_date)).all()
