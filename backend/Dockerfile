FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production

COPY requirements-lock.txt .

RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

RUN groupadd --system app && useradd --system --gid app app
USER app

CMD ["python", "-m", "app.deployment"]
