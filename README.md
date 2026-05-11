# Lifelikegame - AI-Powered Gamified Goal Management Platform

Lifelikegame is a gamified goal management platform that helps users turn personal goals into scheduled tasks, daily task instances, points, rewards, and AI-generated action plans.

Users can create goals, define recurring tasks, automatically generate daily task instances, complete tasks to earn points, and redeem rewards. The system also integrates an AI planner using Gemini API to generate structured goal and task plans from natural language input.

## Features

- User registration and JWT-based authentication
- Goal creation and progress tracking
- Task creation under each goal
- Daily and weekly task scheduling
- Automatic task instance generation
- Task completion with scoring levels
- Point ledger for tracking earned and spent points
- Reward creation and redemption
- AI planner that generates goal and task plans from user prompts
- Dockerized frontend, backend, and PostgreSQL setup

## Tech Stack

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- Axios

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic

### Authentication
- JWT
- python-jose
- passlib / bcrypt

### AI
- Gemini API
- Prompt engineering
- Structured JSON output

### DevOps / Testing
- Docker
- Docker Compose
- Pytest
- HTTPX
- GitHub Actions
- APScheduler