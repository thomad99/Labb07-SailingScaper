from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ✅ Define Base for ORM Models
Base = declarative_base()

# ✅ Define Race Results Table
class RaceResult(Base):
    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position = Column(Integer, nullable=False)
    sail_number = Column(String(50), nullable=True)
    boat_name = Column(String(100), nullable=True)
    skipper = Column(String(100), nullable=True)
    yacht_club = Column(String(100), nullable=True)
    results = Column(Text, nullable=True)
    total_points = Column(Integer, nullable=False)

# ✅ Get DATABASE_URL securely from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL. Set it in Render environment variables.")

# ✅ Create Database Engine
engine = create_engine(DATABASE_URL)

# ✅ Create Tables if They Don't Exist
Base.metadata.create_all(engine)

# ✅ Create a Session Factory
SessionLocal = sessionmaker(bind=engine)
