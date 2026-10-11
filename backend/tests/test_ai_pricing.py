import json
from dataclasses import replace
from decimal import Decimal

import pytest

from app.ai_planner.observation import CallObservation, TokenUsage
from app.ai_planner.pricing import estimate_cost, load_price_profiles
from app.core.config import Settings


def profile_data(**kwargs):
    return dict(provider="gemini", model="test", version="v1", currency="USD",
                input="1", cached_input="0.5", output="2", thinking="2", tool_input="1", **kwargs)


def sample_snapshot():
    observation = CallObservation()
    observation.begin_dispatch()
    observation.attempt()
    observation.capture_usage(TokenUsage(prompt_tokens=1000, cached_input_tokens=200,
                                        output_tokens=100, thinking_tokens=50, tool_input_tokens=0, total_tokens=1150))
    observation.finish()
    return observation.snapshot()


@pytest.mark.parametrize("attempts,status", [(1, "estimated"), (3, "partial"), (None, "partial")])
def test_gemini_bucket_cost_arithmetic(attempts, status):
    profile = load_price_profiles(json.dumps([profile_data()]))[("gemini", "test")]
    snapshot = replace(sample_snapshot(), attempts=attempts, retry_count=None if attempts is None else attempts - 1)
    estimate = estimate_cost(snapshot, profile)
    assert estimate.amount == Decimal("0.001200000000")
    assert (estimate.status, estimate.currency, estimate.version) == (status, "USD", "v1")


@pytest.mark.parametrize("updates", [
    {"prompt_tokens": None}, {"cached_input_tokens": None}, {"thinking_tokens": None},
    {"cached_input_tokens": 1001}, {"total_tokens": 999},
])
def test_missing_or_inconsistent_buckets_mean_unknown(updates):
    snapshot = sample_snapshot()
    snapshot = replace(snapshot, tokens=replace(snapshot.tokens, **updates))
    profile = load_price_profiles(json.dumps([profile_data()]))[("gemini", "test")]
    assert estimate_cost(snapshot, profile).amount is None


@pytest.mark.parametrize("raw", [None, "", "PRIVATE invalid JSON", "{}", '[{"secret":"PRIVATE"}]',
                                      json.dumps([profile_data(), profile_data()])])
def test_invalid_optional_configuration_is_safe(raw, caplog):
    assert load_price_profiles(raw) == {}
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize("rate", ["-1", "NaN", "Infinity", "1e999999", 1, True])
def test_invalid_and_extreme_prices_are_safe(rate):
    data = profile_data()
    data["input"] = rate
    assert load_price_profiles(json.dumps([data])) == {}


def test_exact_model_price_matching_and_missing_profile():
    profiles = load_price_profiles(json.dumps([profile_data()]))
    assert ("gemini", "test-v2") not in profiles
    assert estimate_cost(sample_snapshot(), None).amount is None
    assert estimate_cost(sample_snapshot(), None).status == "unknown"


def test_explicit_zero_rates_are_valid_but_missing_counts_are_not():
    data = profile_data()
    for key in ("input", "cached_input", "output", "thinking", "tool_input"):
        data[key] = "0"
    profile = load_price_profiles(json.dumps([data]))[("gemini", "test")]
    assert estimate_cost(sample_snapshot(), profile).amount == Decimal("0")
    snapshot = replace(sample_snapshot(), tokens=TokenUsage(prompt_tokens=0))
    assert estimate_cost(snapshot, profile).amount is None


def test_malformed_optional_pricing_does_not_reject_settings():
    assert Settings(ai_price_profiles="not json", _env_file=None).ai_price_profiles == "not json"
