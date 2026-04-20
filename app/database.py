import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DEFAULT_LOCAL_DATABASE_URL = (
    "mysql+pymysql://root:1234@127.0.0.1:3306/museum_ai?charset=utf8mb4"
)

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_LOCAL_DATABASE_URL)

engine_kwargs = {
    "echo": True
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()