from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Try to import from config, fall back to environment variables if config is missing
try:
    from config import DB_URL
except ImportError:
    DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sailing_results")
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
