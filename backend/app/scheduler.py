from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db import SessionLocal
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator

settings = get_settings()

TIMEZONE = settings.timezone
SCHEDULER_ENABLED = settings.scheduler_enabled

scheduler = AsyncIOScheduler(timezone=ZoneInfo(TIMEZONE))

def run_generate_task_instances_for_today():
  db = SessionLocal()
  try:
    mediator = build_generate_task_instances_mediator(db)
    target_date = datetime.now(ZoneInfo(TIMEZONE)).date()
    return mediator.send(GenerateDailyTaskInstancesCommand(
      target_date=target_date,
    ))
  finally:
    db.close()


def start_scheduler():

  if not SCHEDULER_ENABLED:
    return

  if not scheduler.running:
    scheduler.add_job(
      run_generate_task_instances_for_today,
      trigger="cron",
      hour =0,
      minute=0,
      id="generate_task_instances_daily",
      replace_existing=True
    )
    scheduler.start()

def stop_scheduler():
  if scheduler.running:
    scheduler.shutdown()

