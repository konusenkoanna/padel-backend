
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Match(Base):
    __tablename__ = "matches"
    id = Column(String, primary_key=True)
    players = Column(JSON)
    sets = Column(JSON)
    game_score = Column(JSON)
    history = Column(JSON)
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="in_progress")

engine = create_engine("sqlite:///padel.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
