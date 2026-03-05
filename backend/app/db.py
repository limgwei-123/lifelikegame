import os
from dotenv import load_dotenv

from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
  raise RuntimeError ("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush= False, bind= engine)

def db_ping() -> str:
  with engine.connect() as conn:
    version = conn.execute(text("SELECT version();")).scalar()
  return version