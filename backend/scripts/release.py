"""Deploy only a successful main CI image, with explicit migration consent.

Requires Python 3, Docker Compose and authenticated GitHub CLI on the server.
This helper never builds an unverified image or deletes database volumes.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "limgwei-123/lifelikegame"


def run(*args, env=None):
    result = subprocess.run(list(args), cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed; deployment stopped. Inspect that command locally.")
    return result.stdout.strip()


def validate_ci_run(data, sha, repository):
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("A full Git commit SHA is required")
    if (data.get("status") != "completed" or data.get("conclusion") != "success"
            or data.get("event") != "push" or data.get("head_branch") != "main"
            or data.get("head_sha") != sha
            or data.get("path", "").split("@", 1)[0] != ".github/workflows/ci.yml"
            or data.get("repository", {}).get("full_name", "").lower() != repository.lower()):
        raise ValueError("Release requires successful main CI for the exact checked-out commit")


def compose_environment(image, env_file):
    # Compose shell variables override --env-file. Remove every interpolated
    # deployment key and explicit file key, preserving only unrelated host tools'
    # environment (PATH, Docker context, authentication, etc.).
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    contents = Path(env_file).read_text(encoding="utf-8-sig")
    keys = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", compose))
    keys.update(re.findall(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", contents, re.MULTILINE))
    return {**{key: value for key, value in os.environ.items() if key not in keys}, "BACKEND_IMAGE": image}


def release(run_id, env_file, *, apply_migrations=False, repository=REPOSITORY):
    if not apply_migrations:
        raise ValueError("Explicit --apply-migrations approval is required before deployment")
    env_file = Path(env_file).resolve(strict=True)
    if run("git", "status", "--porcelain"):
        raise ValueError("Release checkout must be clean and match the CI commit")
    sha = run("git", "rev-parse", "HEAD")
    data = json.loads(run("gh", "api", f"repos/{repository}/actions/runs/{int(run_id)}"))
    validate_ci_run(data, sha, repository)
    run("docker", "info", "--format", "{{.ServerVersion}}")
    image = "lifelikegame-backend:" + sha
    env = compose_environment(image, env_file)
    compose = ["docker", "compose", "--env-file", str(env_file), "-f", str(ROOT / "docker-compose.production.yml")]
    lock = ROOT / ".lifelikegame-release.lock"
    lock.mkdir()  # Atomic, single-host protection against overlapping releases.
    try:
        with TemporaryDirectory(prefix="lifelikegame-release-") as directory:
            run("gh", "run", "download", str(run_id), "--repo", repository,
                "--name", "backend-image-" + sha, "--dir", directory)
            run("docker", "load", "--input", str(Path(directory) / "backend-image.tar"))
        label = run("docker", "image", "inspect", image, "--format",
                    '{{index .Config.Labels "org.opencontainers.image.revision"}}')
        if label != sha:
            raise ValueError("Image revision does not match verified CI")
        run(*compose, "config", "--quiet", env=env)
        # Verify secrets, HTTPS origin and trusted proxy settings before downtime.
        run(*compose, "run", "--rm", "--no-deps", "--entrypoint", "python", "api",
            "-m", "app.deployment", "--check", env=env)
        run(*compose, "stop", "api", env=env)
        run(*compose, "up", "--detach", "--no-build", "--wait", "--wait-timeout", "180", "db", "api", env=env)
    finally:
        lock.rmdir()
    print(f"Released {sha}; production readiness passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=int)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--apply-migrations", action="store_true")
    options = parser.parse_args()
    try:
        release(options.run_id, options.env_file, apply_migrations=options.apply_migrations, repository=options.repository)
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(str(error)) from None
