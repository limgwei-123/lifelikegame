import json
import logging
from typing import Callable, NoReturn

from google import genai
import httpx
from google.genai import errors, types

from app.ai_planner.errors import (
    AIConfigurationError, AIInvalidOutputError, AIProviderError,
    AIRateLimitedError, AITimeoutError, AIUnavailableError,
)
from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.providers.base import PlannerRequest, PlannerResult
from app.ai_planner.observation import CallObservation, TokenUsage, safe_log, safe_observe


def _reject_non_json_number(value: str) -> NoReturn:
    raise ValueError(f"AI Planner output contains an invalid JSON number: {value}")


class GeminiPlannerProvider:
    def __init__(self, *, api_key: str | None, model: str | None, before_send: Callable[[], None] | None = None,
                 observation: CallObservation | None = None):
        self.api_key = api_key
        self.model = model
        self.before_send = before_send
        self.observation = observation

    def generate_plan(self, request: PlannerRequest) -> PlannerResult:
        try:
            return self._generate_plan(request)
        finally:
            safe_observe(self.observation, "finish")

    def _capture_usage(self, response: object) -> None:
        if self.observation is None:
            return
        try:
            metadata = getattr(response, "usage_metadata", None)
            tokens = TokenUsage(
                prompt_tokens=getattr(metadata, "prompt_token_count", None),
                output_tokens=getattr(metadata, "candidates_token_count", None),
                total_tokens=getattr(metadata, "total_token_count", None),
                cached_input_tokens=getattr(metadata, "cached_content_token_count", None),
                thinking_tokens=getattr(metadata, "thoughts_token_count", None),
                tool_input_tokens=getattr(metadata, "tool_use_prompt_token_count", None),
            )
            safe_observe(self.observation, "capture_usage", tokens)
        except Exception:
            safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_observation_failed")

    def _generate_plan(self, request: PlannerRequest) -> PlannerResult:
        if not self.api_key or not self.model:
            raise AIConfigurationError()

        prompt = build_generate_plan_prompt(
            user_prompt=request.user_prompt,
            conversation_history=request.conversation_history,
        )
        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=20000,
                retry_options=types.HttpRetryOptions(
                    attempts=3, initial_delay=1, max_delay=4, exp_base=2, jitter=1,
                    http_status_codes=[408, 429, 500, 502, 503, 504],
                ),
                client_args={"event_hooks": {"request": [
                    lambda request: safe_observe(self.observation, "attempt"),
                ]}} if self.observation is not None else None,
            ),
        )
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=PlannerResult.model_json_schema(),
            )
            if self.before_send is not None:
                self.before_send()
            safe_observe(self.observation, "begin_dispatch")
            try:
                # SDK owns all retries; admission runs once per logical request.
                response = client.models.generate_content(model=self.model, contents=prompt, config=config)
            except httpx.TimeoutException as exc:
                raise AITimeoutError() from exc
            except httpx.TransportError as exc:
                raise AIUnavailableError() from exc
            except errors.APIError as exc:
                if exc.code in (408, 504):
                    raise AITimeoutError() from exc
                if exc.code == 429:
                    raise AIRateLimitedError() from exc
                if exc.code in (401, 403, 404):
                    raise AIConfigurationError() from exc
                if exc.code in (500, 502, 503):
                    raise AIUnavailableError() from exc
                raise AIProviderError() from exc
            except ValueError as exc:
                raise AIInvalidOutputError() from exc
            self._capture_usage(response)
        finally:
            client.close()
        try:
            raw = response.text
            if not raw or not raw.strip():
                raise ValueError("Empty response")
            data = json.loads(raw, parse_constant=_reject_non_json_number)
            result = PlannerResult.model_validate(data, strict=True)
        except ValueError as exc:
            raise AIInvalidOutputError() from exc
        # Keep existing defaults, but only after the output passes validation.
        if result.plan is not None:
            for task in result.plan.tasks:
                if task.schedule_type == "daily":
                    task.schedule_value_json = {}
                elif not task.schedule_value_json.get("days"):
                    task.schedule_value_json = {"days": [1, 3, 5]}
        return result
