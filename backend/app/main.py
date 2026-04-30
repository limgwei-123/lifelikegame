from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import db_ping
from app.routers.public import router as public_router
from app.routers.protected import router as protected_router
from app.errors.handlers import register_exception_handlers

from contextlib import asynccontextmanager

from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
  start_scheduler()
  yield
  stop_scheduler()

app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(protected_router)



@app.get("/health")
def health():
  return {"status": "ok"}

@app.get("/db-health")
def db_health():
  version = db_ping()
  return {"db":"ok", "version": version}
