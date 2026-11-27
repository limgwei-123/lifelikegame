"""Seed the vendor-result boundary ONLY in the disposable frontend review DB."""
import json
import sys
from uuid import UUID

import app.main  # register the production model graph
from app.db import engine
from app.ai_planner.dependencies import build_ai_draft_service
from app.ai_planner.providers.base import GeneratedPlan
from app.core.unit_of_work import build_unit_of_work
from app.users.models import User
from sqlalchemy.orm import Session

assert engine.url.database == "frontend_review", "Refusing a non-review database"
payload = json.load(sys.stdin)
with Session(engine) as db, build_unit_of_work(db).begin():
    user = db.get(User, UUID(payload["user_id"]))
    assert user is not None and user.email.startswith("ai-browser-") and user.email.endswith("@example.com")
    saved = build_ai_draft_service(db).save_generated(user_id=user.id, plan=GeneratedPlan.model_validate(payload["plan"]))
    result = saved.model_dump_json()
print(result)
