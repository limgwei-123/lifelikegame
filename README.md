# Lifelikegame

Lifelikegame is a gamified personal goal management platform. It helps users break long-term goals into tasks, schedules, and daily task instances. Users earn points by completing tasks and can redeem those points for rewards. The project also includes an AI Planner that turns natural language goal descriptions into structured goal and task plans.

## Core Features

- User signup, login, and JWT-based authentication
- Goal creation, listing, updating, and deletion
- Task creation under specific goals
- Daily and weekly task scheduling
- Automatic daily task instance generation
- Task completion with scoring levels
- Point ledger and current point balance
- Reward creation and point-based reward redemption
- AI Planner for generating goal and task plans from chat input
- Docker Compose setup for frontend, backend, and PostgreSQL
- Backend test coverage with Pytest

## Tech Stack

Frontend:

- React 18
- Vite
- Plain CSS
- Fetch API

Backend:

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- APScheduler

Authentication and AI:

- JWT
- python-jose
- passlib / bcrypt
- Google Gemini API through `google-genai`

Testing and DevOps:

- Pytest
- HTTPX
- Docker
- Docker Compose

## Project Structure

```text
lifelikegame/
├── backend/
│   ├── app/
│   │   ├── auth/                 # Signup, login, JWT authentication
│   │   ├── users/                # User profile data
│   │   ├── goals/                # Goal module
│   │   ├── tasks/                # Task module
│   │   ├── task_schedules/       # Task schedule module
│   │   ├── task_instances/       # Daily task instances
│   │   ├── scoring_schemes/      # Scoring schemes
│   │   ├── point_ledgers/        # Point ledger records
│   │   ├── rewards/              # Rewards
│   │   ├── redemptions/          # Reward redemption records
│   │   ├── workflows/            # Cross-module business workflows
│   │   ├── ai_planner/           # AI plan generation
│   │   ├── scheduler.py          # Scheduled task instance generation
│   │   ├── db.py                 # Database connection
│   │   └── main.py               # FastAPI entry point
│   ├── alembic/                  # Database migrations
│   ├── tests/                    # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                  # Frontend API client
│   │   ├── components/           # Shared UI components
│   │   ├── pages/                # Application pages
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── README.md
└── readme_ai.md
```

## Environment Variables

The project expects a `.env` file in the repository root. The existing `.env .example` file can be used as a reference.

```env
POSTGRES_USER=lifelikegame
POSTGRES_PASSWORD=your_password
POSTGRES_DB=lifelikegame
DATABASE_URL=postgresql://lifelikegame:your_password@db:5432/lifelikegame

TEST_DATABASE_URL=postgresql://lifelikegame:your_password@localhost:5433/lifelikegame_test

TIMEZONE=Asia/Kuala_Lumpur

JWT_SECRET=your_jwt_secret
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

AI_API_KEY=your_gemini_api_key
AI_MODEL=gemini-2.0-flash

LOGIN_REQUESTS_PER_MINUTE=10
SIGNUP_REQUESTS_PER_HOUR=10
AI_REQUESTS_PER_MINUTE=3
AI_DAILY_REQUEST_LIMIT=10
```

The positive integer request limits apply per IP for login/signup and per
authenticated user for AI generation. Successful and failed attempts count
toward a fixed window starting with its first attempt. A rejected request returns `429`, code
`REQUEST_RATE_LIMITED`, and a `Retry-After` header in seconds. Rejected AI
bursts do not call the provider or consume the database-backed daily quota.

Short windows use one API process's memory and reset on restart; do not run
multiple API workers/replicas with this limiter. Expired counters are reclaimed,
and at 1024 active endpoint/identity counters, new identities are temporarily
rejected without evicting existing counters. IPs come from the ASGI client;
configure only trusted proxy addresses at the server before public deployment,
and keep direct access to the backend restricted behind that proxy. Clients
sharing a public IP share login/signup limits.

The frontend API base URL can be configured with `VITE_API_BASE_URL`. If it is not set, the frontend defaults to `http://localhost:8000`.

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Run With Docker

From the repository root:

```bash
docker compose up --build
```

Service URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- PostgreSQL host port: `5433`

When the backend starts, APScheduler is also started. It generates task instances every day at `00:00` based on the configured `TIMEZONE`.

## Database Migrations

The default Compose file is for local development and overrides the image's
production startup command. Apply development migrations explicitly with
`docker compose exec api alembic upgrade head` when you choose to upgrade that
database. Production uses the separate procedure below.

Run Alembic migrations from the backend directory:

```bash
cd backend
alembic upgrade head
```

Alembic reads `DATABASE_URL` from the root `.env` file.

## Production Deployment (Single Host)

Use `docker-compose.production.yml` by itself, not merged with the development
file. It runs one API container/worker with one scheduler, uses a separate
production database volume, publishes no database port, and binds the API to
`127.0.0.1:8000`. There is no reload or source-code mount. The image runs as a
non-root user and excludes tests, scripts, local secrets and virtualenv files.
The current lock still includes test libraries; test source files are excluded.

Before exposing the service, configure an HTTPS reverse proxy on the host and
forward to `127.0.0.1:8000`. Set `FORWARDED_ALLOW_IPS` to the actual proxy source
address observed by the API container, which may be a Docker gateway rather
than `127.0.0.1`. Restrict direct access, replace forwarded headers at that
trusted proxy, and never trust `*`. TLS, DNS, firewall and hosting configuration
are external prerequisites, not configured by this repository. Keep one API
worker/replica and stop the old API before starting a new version; do not use
rolling overlap. Revisit scheduler and rate-limit design before scaling.

The supported release path is a successful `main` push of the **exact commit**:
CI tests first, then builds and smoke-tests the production image against a
disposable PostgreSQL container. Only then does it publish the downloadable
`backend-image-<commit SHA>` artifact (7-day retention, current image platform
is Linux/AMD64). Failed CI produces no releasable artifact. This gate protects
the release helper; repository administrators can still bypass branch rules or
run Docker manually. Require the CI checks in repository settings to also block
merges; those account settings must be configured separately.

On the server, install Python 3, Docker Compose and GitHub CLI (`gh`), authenticate
`gh` with repository/Actions read access, and check out the same commit with a
clean worktree. Copy `.env.production.example` to ignored `.env.production` and
fill it in. Generate separate random database/JWT secrets, for example with
`python -c "import secrets; print(secrets.token_hex(32))"`. Keep the DB password
in `POSTGRES_PASSWORD` and `DATABASE_URL` identical; URL-encode it if it contains
reserved URL characters. Production requires at least 32 characters for
`JWT_SECRET` and a single HTTPS `FRONTEND_URL`. Only that browser origin is
allowed by CORS. AI calls additionally require valid `AI_API_KEY` and `AI_MODEL`.

After separately approving migration of the production database, run:

```bash
python backend/scripts/release.py RUN_ID --env-file .env.production --apply-migrations
```

`RUN_ID` is the successful CI run's number shown in its GitHub URL, not a commit
SHA. The helper verifies its repository, workflow, branch, conclusion and commit,
downloads the CI artifact, verifies the image revision, preflights configuration,
then stops the old API and waits for the replacement to become ready. It holds
a local `.lifelikegame-release.lock` directory to prevent concurrent releases;
after a host/process crash, check no release is running before removing a stale
empty lock. It does not deploy automatically after a push and never rebuilds
from unverified working files. Do not change DB credentials on an existing
PostgreSQL volume without a separate credential-rotation procedure.
Deployment values come from the explicitly selected env file; inherited shell
values with those names are removed before Compose runs. Keep this file
self-contained rather than referring to unrelated shell variables.

The image entry point is `python -m app.deployment`: validate production config,
run `alembic upgrade head`, then start exactly one Uvicorn worker. A migration
failure exits without serving traffic. Existing invalid records are reported by
the migration and require a separate data-handling decision; there is no automatic
repair, deletion or downgrade. Do not run another migration command concurrently.
The API restart policy is deliberately disabled: after a host/container failure,
use the verified release command again, or start the same approved image after
checking the cause. This avoids an unattended migration retry loop.

`GET /health` is liveness; `GET /db-health` returns 200 when PostgreSQL responds,
otherwise a safe 503. Production logs retain event identifiers, request context
and exception types while omitting SQL values, arbitrary dependency messages,
request/access logs and tracebacks. Detailed debugging should use controlled
local reproduction instead of enabling sensitive production trace output.

To reproduce the image acceptance checks locally without touching an existing DB:

```bash
docker build -t lifelikegame-backend:check ./backend
python backend/scripts/smoke_release.py --image lifelikegame-backend:check
```

The smoke script creates randomly named containers/network, verifies migration,
authenticated task/reward flows and DB outage/recovery, checks migration refusal
on invalid test history, then removes only its own temporary resources.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

Backend tests use Pytest. Make sure `TEST_DATABASE_URL` points to an available test database, then run:

```bash
cd backend
pytest
```

The test suite covers users, authentication, goals, tasks, task schedules, task instances, points, rewards, redemptions, scoring schemes, and workflows.

## Main API Areas

Public endpoints:

- `POST /auth/signup`: Create a user account
- `POST /auth/login`: Log in and receive a JWT
- `GET /health`: API health check
- `GET /db-health`: Database health check

JWT-protected endpoint groups:

- `/users`: User information
- `/goals`: Goal management
- `/tasks`: Task management
- `/task_schedules`: Task schedules
- `/task_instances`: Task instances
- `/scoring_schemes`: Scoring schemes
- `/point_ledgers`: Point ledger records and balance
- `/rewards`: Reward management
- `/redemptions`: Redemption records
- `/workflows`: Combined business workflows
- `/ai-planner`: AI plan generation

### Standalone todos and point posting

`POST /workflows/tasks` creates a task and its optional schedule in one transaction.
The top-level `goal_id` may be omitted or `null` for an ordinary todo, or set to
one of the authenticated user's goals. Existing `/workflows/goals/{goal_id}/tasks`
and `/goals/{goal_id}/tasks` routes remain available. `POST /tasks` creates a
standalone task without a schedule.

Standalone tasks have no scoring scheme and reject scoring configuration. They
use the same one-time/daily/weekly/monthly schedules as goal tasks. Complete a
standalone instance with `POST /task_instances/{id}/complete` and `{}`: its score
stays zero and no point ledger entry is created. Goal instances can also omit
`completion_level` when their saved scoring snapshot has exactly one level;
multiple levels still require an explicit selection.

`POST /point_ledgers` now returns **403** for authenticated clients (**401** for
unauthenticated requests). Task completion and reward redemption post entries
internally; listing, balance, and reconciliation endpoints remain readable.

These changes require migration `e8a4c2b6d901`. Apply it only after separately
approving the target database migration. Existing goal tasks are preserved; a
downgrade refuses to proceed while any standalone tasks remain, including
soft-deleted ones, rather than deleting or reassigning them.

## AI Planner Workflow

The AI Planner lives in `backend/app/ai_planner`. It builds a prompt from the user input and conversation history, sends it to the Gemini API, and expects the model to return JSON only.

The main AI response statuses are:

- `need_more_info`: More information is required before a plan can be generated
- `plan_ready`: A plan preview is ready for the user to review
- `start_generate`: The user has confirmed that the plan should be created

The frontend AI page displays the plan preview. After user confirmation, the frontend calls:

```text
POST /workflows/ai/confirm
```

The backend then creates the goal, tasks, and task schedules from the AI-generated plan.

## Business Flow

1. The user signs up and logs in.
2. The user creates a goal manually or generates one through AI Planner.
3. The user creates tasks under the goal.
4. The user configures daily or weekly schedules for those tasks.
5. The system generates task instances for matching dates.
6. The user completes task instances and selects a completion level.
7. The system writes point ledger records based on the scoring scheme.
8. The user redeems rewards using earned points.

## Notes

- The frontend currently uses React + Vite + JSX, not TypeScript.
- Frontend styling is mainly defined in `frontend/src/styles.css`; Tailwind is not configured.
- Some update and delete routes use `POST /resource/{id}` or `POST /resource/{id}/delete` instead of traditional REST `PUT/PATCH/DELETE` routes.
- AI Planner requires `AI_API_KEY` and `AI_MODEL`; without them, AI generation will not work.
- `DATABASE_URL` is required for backend startup. The app raises an error if it is missing.


## Demo Account

Email: user@example.com
Password: string
