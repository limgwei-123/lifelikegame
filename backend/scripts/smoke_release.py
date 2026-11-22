"""Exercise the production image using ONLY disposable, randomly named resources.

Run from the repository root: python backend/scripts/smoke_release.py --image TAG
No host database URL, secret file, existing container or volume is used.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from release import compose_environment


def docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def wait_for(check, label, seconds=90):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if check():
                return
        except (OSError, URLError, subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise RuntimeError(f"Timed out: {label}")


def smoke(image):
    docker("info", "--format", "{{.ServerVersion}}")
    # Resolve the real production config with explicit test values, never .env.
    root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix="lifelikegame-compose-check-") as directory:
        env_file = Path(directory) / "empty.env"
        selected_url = "postgresql://postgres:smoke-only-password@db:5432/lifelikegame_smoke"
        env_file.write_text("POSTGRES_PASSWORD=smoke-only-password\nDATABASE_URL=" + selected_url
                            + "\nJWT_SECRET=smoke-only-test-secret-longer-than-32-characters"
                            + "\nFRONTEND_URL=https://app.example.com\n", encoding="utf-8")
        config_env = compose_environment(image, env_file)
        result = subprocess.run(["docker", "compose", "--env-file", str(env_file), "-f",
                                 str(root / "docker-compose.production.yml"), "config", "--format", "json"],
                                env=config_env, check=True, capture_output=True, text=True)
        services = json.loads(result.stdout)["services"]
        assert not services["db"].get("ports")
        assert not services["api"].get("volumes") and not services["api"].get("build")
        assert services["api"]["ports"][0]["host_ip"] == "127.0.0.1"
        assert services["api"]["environment"]["APP_ENV"] == "production"
        assert services["api"]["environment"]["DATABASE_URL"] == selected_url
    prefix = "lifelikegame-smoke-" + uuid4().hex[:12]
    db, api, network = prefix + "-db", prefix + "-api", prefix + "-net"
    owned_containers = []
    network_created = False
    base_url = None

    def request(method, path, payload=None, headers=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(base_url + path, data=data, method=method,
                      headers={"Content-Type": "application/json", **(headers or {})})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.status, json.loads(body), response.headers

    def expect(method, path, payload=None, headers=None, status=200):
        actual, data, response_headers = request(method, path, payload, headers)
        if actual != status:
            raise AssertionError(f"{method} {path}: expected {status}, received {actual}")
        return data

    def sql(statement):
        return docker("exec", db, "psql", "-U", "postgres", "-d", "lifelikegame_smoke",
                      "-v", "ON_ERROR_STOP=1", "-tAc", statement).stdout.strip()

    env = ["-e", "DATABASE_URL=postgresql://postgres:smoke-only-password@" + db + ":5432/lifelikegame_smoke",
           "-e", "JWT_SECRET=smoke-only-random-test-secret-with-more-than-32-characters",
           "-e", "FRONTEND_URL=https://app.example.com", "-e", "APP_ENV=production",
           "-e", "WEB_CONCURRENCY=4"]
    try:
        docker("network", "create", network)
        network_created = True
        owned_containers.append(db)
        docker("run", "-d", "--name", db, "--network", network,
               "-e", "POSTGRES_DB=lifelikegame_smoke", "-e", "POSTGRES_PASSWORD=smoke-only-password", "postgres:16")
        wait_for(lambda: docker("exec", db, "pg_isready", "-U", "postgres", check=False).returncode == 0,
                 "temporary PostgreSQL")
        docker("run", "--rm", "--network", network, *env, "--entrypoint", "python", image,
               "-m", "app.deployment", "--check")
        assert sql("SELECT to_regclass('public.alembic_version') IS NULL") == "t"
        owned_containers.append(api)
        docker("run", "-d", "--name", api, "--network", network, "-p", "127.0.0.1::8000", *env, image)
        mapping = docker("port", api, "8000/tcp").stdout.strip().splitlines()[0]
        base_url = "http://127.0.0.1:" + mapping.rsplit(":", 1)[1]
        wait_for(lambda: request("GET", "/db-health")[0] == 200, "migrated API")
        assert sql("SELECT count(*) FROM alembic_version") == "1"
        # Inspect the real image, not just the ignore file's text.
        docker("exec", api, "python", "-c",
               "from pathlib import Path; import os; assert os.getuid()!=0; "
               "assert all(not Path('/app',p).exists() for p in ('.venv','tests','scripts','.env'))")
        expect("GET", "/health")
        assert request("GET", "/users/me")[0] in (401, 403)
        for origin, allowed in [("https://app.example.com", True), ("http://localhost:5173", False)]:
            _, _, headers = request("GET", "/health", headers={"Origin": origin})
            assert (headers.get("Access-Control-Allow-Origin") == origin) == allowed

        credentials = {"email": "smoke@example.com", "password": "smoke-password-123"}
        expect("POST", "/auth/signup", credentials, status=201)
        token = expect("POST", "/auth/login", credentials)["access_token"]
        headers = {"Authorization": "Bearer " + token}
        goal = expect("POST", "/goals", {"title": "Smoke goal", "start_date": "2035-01-01"}, headers, 201)
        scheme = expect("POST", "/scoring_schemes", {"title": "Smoke score", "levels_json": {"normal": 10}}, headers, 201)
        workflow = expect("POST", f"/workflows/goals/{goal['id']}/tasks", {
            "task": {"title": "Smoke task", "scoring_scheme_id": scheme["id"]},
            "schedule": {"schedule_type": "once", "schedule_value_json": {}, "start_date": "2035-01-01"},
        }, headers, 201)
        path = f"/task_instances/{workflow['task_instance']['id']}/complete"
        expect("POST", path, {"completion_level": "normal"}, headers)
        expect("POST", path, {"completion_level": "normal"}, headers)
        assert expect("GET", "/point_ledgers/balance", headers=headers)["balance"] == 10
        reward = expect("POST", "/rewards", {"title": "Smoke reward", "cost_points": 3}, headers, 201)
        expect("POST", f"/workflows/rewards/{reward['id']}/redeem", headers=headers)
        assert expect("GET", "/point_ledgers/balance", headers=headers)["balance"] == 7
        assert expect("GET", "/point_ledgers/reconciliation", headers=headers)["is_consistent"] is True
        other = {"email": "other-smoke@example.com", "password": "smoke-password-123"}
        expect("POST", "/auth/signup", other, status=201)
        other_token = expect("POST", "/auth/login", other)["access_token"]
        assert request("GET", f"/goals/{goal['id']}", headers={"Authorization": "Bearer " + other_token})[0] in (403, 404)
        assert sql("SELECT count(*) FROM pg_stat_activity WHERE datname='lifelikegame_smoke'") != "0"
        print("PASS: migrated image, non-root/clean image, production CORS, auth/ownership, task completion and redemption", flush=True)

        docker("stop", "--time", "5", db)
        expect("GET", "/health")
        expect("GET", "/db-health", status=503)
        docker("start", db)
        wait_for(lambda: request("GET", "/db-health")[0] == 200, "database recovery")
        print("PASS: liveness/readiness during database outage and recovery", flush=True)

        # Stop before migrating, exactly as the documented release procedure.
        docker("stop", "--time", "10", api)
        previous = "c3d8f5b0e721"
        docker("run", "--rm", "--network", network, *env, "--entrypoint", "alembic", image, "downgrade", previous)
        sql(f"UPDATE rewards SET cost_points=-1 WHERE id={int(reward['id'])}")
        failed = prefix + "-migration-refusal"
        owned_containers.append(failed)
        docker("run", "-d", "--name", failed, "--network", network, *env, image)
        wait_for(lambda: docker("inspect", "--format", "{{.State.Running}}", failed).stdout.strip() == "false",
                 "invalid-history refusal")
        assert docker("inspect", "--format", "{{.State.ExitCode}}", failed).stdout.strip() == "1"
        assert sql("SELECT version_num FROM alembic_version") == previous
        assert sql(f"SELECT cost_points FROM rewards WHERE id={int(reward['id'])}") == "-1"
        logs = docker("logs", failed).stdout + docker("logs", failed).stderr
        assert "production_startup_failed" in logs
        assert "smoke-only-password" not in logs and "Traceback" not in logs
        print("PASS: invalid historical data refuses startup without repair or version advance", flush=True)
    finally:
        for name in reversed(owned_containers):
            docker("rm", "-f", "-v", name, check=False)
        if network_created:
            docker("network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    smoke(parser.parse_args().image)
