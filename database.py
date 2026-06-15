import os
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./prism.db"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    print("[PRISM] Database: PostgreSQL connection refused. Falling back to local SQLite database.")
    DATABASE_URL = "sqlite:///./prism.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # low/medium/high/critical
    root_cause = Column(Text, nullable=True)
    fix = Column(Text, nullable=True)
    postmortem = Column(Text, nullable=True)
    affected_components = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Automatically create tables when database.py is loaded.
Base.metadata.create_all(bind=engine)

def create_incident(
    title: str,
    severity: str,
    root_cause: str,
    fix: str,
    postmortem: str,
    affected_components: str
) -> Incident:
    """Inserts a new incident into the database."""
    db = SessionLocal()
    try:
        incident = Incident(
            title=title,
            severity=severity,
            root_cause=root_cause,
            fix=fix,
            postmortem=postmortem,
            affected_components=affected_components
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident
    finally:
        db.close()

def get_all_incidents() -> list[Incident]:
    """Fetches all incidents from the database."""
    db = SessionLocal()
    try:
        return db.query(Incident).all()
    finally:
        db.close()
