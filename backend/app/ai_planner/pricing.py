from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import json
import logging

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai_planner.observation import CallSnapshot, safe_log


class TokenPriceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    provider: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    input: Decimal
    cached_input: Decimal
    output: Decimal
    thinking: Decimal
    tool_input: Decimal

    @field_validator("input", "cached_input", "output", "thinking", "tool_input", mode="before")
    @classmethod
    def rate(cls, value: object) -> Decimal:
        if not isinstance(value, str) or len(value) > 128:
            raise ValueError("Rate must be a bounded decimal string")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Invalid decimal rate") from exc
        if not number.is_finite() or number < 0 or number > Decimal("1e12") or number.as_tuple().exponent < -128:
            raise ValueError("Rate out of supported range")
        return number


@dataclass(frozen=True)
class CostEstimate:
    amount: Decimal | None = None
    currency: str | None = None
    version: str | None = None
    status: str = "unknown"


def load_price_profiles(raw: str | None) -> dict[tuple[str, str], TokenPriceProfile]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Expected a list")
        profiles = {}
        for item in data:
            profile = TokenPriceProfile.model_validate(item)
            key = (profile.provider, profile.model)
            if key in profiles:
                raise ValueError("Duplicate profile")
            profiles[key] = profile
        return profiles
    except Exception:
        safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_pricing_configuration_invalid")
        return {}


def estimate_cost(snapshot: CallSnapshot, profile: TokenPriceProfile | None) -> CostEstimate:
    if profile is None:
        return CostEstimate()
    unknown = CostEstimate(currency=profile.currency, version=profile.version)
    usage = snapshot.tokens
    buckets = (usage.prompt_tokens, usage.cached_input_tokens, usage.output_tokens,
               usage.thinking_tokens, usage.tool_input_tokens)
    if any(value is None for value in buckets):
        return unknown
    prompt, cached, output, thinking, tool = buckets
    if cached > prompt or (usage.total_tokens is not None and usage.total_tokens != prompt + output + thinking + tool):
        return unknown
    try:
        with localcontext() as context:
            context.prec = 160
            amount = ((prompt - cached) * profile.input + cached * profile.cached_input
                      + output * profile.output + thinking * profile.thinking + tool * profile.tool_input) / Decimal(1_000_000)
            amount = amount.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP)
            if not amount.is_finite() or amount >= Decimal("1e12"):
                return unknown
        status = "estimated" if snapshot.attempts == 1 else "partial"
        return CostEstimate(amount, profile.currency, profile.version, status)
    except (InvalidOperation, OverflowError):
        return unknown
