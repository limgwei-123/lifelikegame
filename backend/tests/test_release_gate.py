"""The release path must reject CI for the wrong code, source or conclusion."""

import pytest

from scripts.release import release, validate_ci_run


SHA = "a" * 40
REPOSITORY = "limgwei-123/lifelikegame"


def passed_run(**changes):
    return {"status": "completed", "conclusion": "success", "event": "push",
            "head_branch": "main", "head_sha": SHA, "path": ".github/workflows/ci.yml",
            "repository": {"full_name": REPOSITORY}, **changes}


@pytest.mark.parametrize("changes", [
    {"conclusion": "failure"}, {"conclusion": "cancelled"}, {"conclusion": "skipped"},
    {"status": "in_progress"}, {"event": "pull_request"}, {"head_branch": "dev"},
    {"head_sha": "b" * 40}, {"path": ".github/workflows/unrelated.yml"},
    {"repository": {"full_name": "untrusted/fork"}},
])
def test_release_rejects_unverified_run(changes):
    with pytest.raises(ValueError):
        validate_ci_run(passed_run(**changes), SHA, REPOSITORY)


def test_release_accepts_exact_successful_main_ci():
    validate_ci_run(passed_run(), SHA, REPOSITORY)


def test_missing_migration_consent_stops_before_any_command(monkeypatch, tmp_path):
    from scripts import release as module
    monkeypatch.setattr(module, "run", lambda *args, **kwargs: pytest.fail("No commands before explicit consent"))
    with pytest.raises(ValueError, match="apply-migrations"):
        release(123, tmp_path / "production.env")


def test_explicit_release_file_wins_over_stale_shell_values(monkeypatch, tmp_path):
    from scripts import release as module
    env_file = tmp_path / "production.env"
    env_file.write_text("DATABASE_URL=postgresql://production/db\nCUSTOM_OPTION=file-value\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unrelated-development-db/db")
    monkeypatch.setenv("CUSTOM_OPTION", "stale-shell-value")
    monkeypatch.setenv("BACKEND_IMAGE", "unverified:latest")
    environment = module.compose_environment("verified:sha", env_file)
    assert "DATABASE_URL" not in environment
    assert "CUSTOM_OPTION" not in environment
    assert environment["BACKEND_IMAGE"] == "verified:sha"
