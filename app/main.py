from fastapi import FastAPI
from app.db import db_ping

app = FastAPI()

@app.get("/health")
def health():
  return {"status": "ok"}

@app.get("/db-health")
def db_health():
  version = db_ping()
  return {"db":"ok", "version": version}