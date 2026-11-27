"""A successful response must be visible to the next worker immediately."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.goals.models import Goal
from app.rewards.models import Reward
from app.scoring_schemes.models import ScoringScheme


@pytest.mark.parametrize("path,model,extra", [
    ("/goals", Goal, {}),
    ("/scoring_schemes", ScoringScheme, {"levels_json": {"done": 1}}),
    ("/rewards", Reward, {"cost_points": 1}),
])
def test_create_commits_before_success_headers(client, db, auth_user, path, model, extra):
    title = "response-visibility-" + uuid4().hex
    visible_at_headers = []

    async def observe_response(scope, receive, send):
        async def observe_send(message):
            if message["type"] == "http.response.start" and message["status"] == 201:
                # A separate connection models a follow-up hitting another worker.
                with Session(db.get_bind()) as reader:
                    visible_at_headers.append(reader.scalar(select(model.id).where(
                        model.title == title, model.user_id == UUID(auth_user["user_id"]),
                    )) is not None)
            await send(message)
        await app(scope, receive, observe_send)

    observer = TestClient(observe_response)
    try:
        response = observer.post(path, json={"title": title, **extra}, headers={
            "Authorization": "Bearer " + auth_user["access_token"],
        })
    finally:
        observer.close()
    assert response.status_code == 201, response.text
    assert visible_at_headers == [True], "201 was sent before the write committed"
