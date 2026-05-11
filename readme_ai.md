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
```

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

Run Alembic migrations from the backend directory:

```bash
cd backend
alembic upgrade head
```

Alembic reads `DATABASE_URL` from the root `.env` file.

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
