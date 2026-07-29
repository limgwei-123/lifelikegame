from app.core.config import get_settings

from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, declarative_base

settings = get_settings()
DATABASE_URL = settings.database_url

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush= False, bind= engine)

Base = declarative_base()

def db_ping() -> None:
  with engine.connect() as conn:
    conn.execute(text("SELECT 1"))

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
