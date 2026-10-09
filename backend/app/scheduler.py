from datetime import datetime
import logging
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.core.behaviors import bind_request_id, reset_request_id
from app.core.config import get_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db import SessionLocal
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator

settings = get_settings()

TIMEZONE = settings.timezone
SCHEDULER_ENABLED = settings.scheduler_enabled

scheduler = AsyncIOScheduler(timezone=ZoneInfo(TIMEZONE))
logger = logging.getLogger(__name__)

def run_generate_task_instances_for_today():
  request_id = str(uuid4())
  token = bind_request_id(request_id)
  started_at = perf_counter()
  db = None
  target_date = None
  try:
    target_date = datetime.now(ZoneInfo(TIMEZONE)).date()
    db = SessionLocal()
    mediator = build_generate_task_instances_mediator(db)
    result = mediator.send(GenerateDailyTaskInstancesCommand(
      target_date=target_date,
    ))
    logger.info("scheduler_generation_completed", extra={
      "request_id": request_id,
      "target_date": target_date.isoformat(),
      "processed_count": result.processed_count,
      "created_count": result.created_count,
      "outcome": "success",
      "duration_ms": round((perf_counter() - started_at) * 1000, 3),
    })
    return result
  except Exception:
    logger.exception("scheduler_generation_failed", extra={
      "request_id": request_id,
      "target_date": target_date.isoformat() if target_date else None,
      "processed_count": None,
      "created_count": None,
      "outcome": "failure",
      "duration_ms": round((perf_counter() - started_at) * 1000, 3),
    })
    raise
  finally:
    try:
      if db is not None:
        db.close()
    finally:
      reset_request_id(token)


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

