from fastapi import FastAPI
from app.db import db_ping
from app.auth.router import router as auth_router

app = FastAPI()
app.include_router(auth_router)

@app.get("/health")
def health():
  return {"status": "ok"}

@app.get("/db-health")
def db_health():
  version = db_ping()
  return {"db":"ok", "version": version}