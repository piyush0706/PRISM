"""
=========================================================
PRISM - Database Module
=========================================================
Handles SQLAlchemy engine, session, and ORM models.
Supports:
  - PostgreSQL (production on Render)
  - SQLite   (local fallback — zero config)
=========================================================
"""

import os
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

load_dotenv()

# ─────────────────────────────────────────
# 1. Resolve DATABASE_URL
#    - Render provides postgresql:// URLs;
#      SQLAlchemy 1.4+ needs postgresql+psycopg2://
# ─────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    # No DB configured → use local SQLite
    DATABASE_URL = "sqlite:///./prism.db"
    print("[PRISM DB] No DATABASE_URL set. Using local SQLite fallback (prism.db).")
elif DATABASE_URL.startswith("postgres://"):
    # Heroku / older Render style → fix dialect
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    print("[PRISM DB] Converted postgres:// → postgresql+psycopg2://")
elif DATABASE_URL.startswith("postgresql://"):
    # Render standard style → ensure psycopg2 dialect
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print("[PRISM DB] Using PostgreSQL via psycopg2.")

# ─────────────────────────────────────────
# 2. Engine Configuration
# ─────────────────────────────────────────
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL — connection pool tuning for Render free tier
    engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,   # recycle stale connections
        "pool_recycle": 300,     # recycle connections every 5 min
    }

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
    # Verify connection is valid on startup
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"[PRISM DB] ✅ Database connected successfully.")
except Exception as exc:
    print(f"[PRISM DB] ⚠️  PostgreSQL connection failed: {exc}")
    print("[PRISM DB] Falling back to local SQLite database (prism.db).")
    DATABASE_URL = "sqlite:///./prism.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# ─────────────────────────────────────────
# 3. Session & Base
# ─────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ─────────────────────────────────────────
# 4. ORM Models
# ─────────────────────────────────────────
class Incident(Base):
    __tablename__ = "incidents"

    id                 = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title              = Column(Text, nullable=False)
    severity           = Column(String(50), nullable=False)   # low / medium / high / critical
    root_cause         = Column(Text, nullable=True)
    fix                = Column(Text, nullable=True)
    postmortem         = Column(Text, nullable=True)
    affected_components = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.datetime.utcnow)


# Create tables automatically on startup
Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────
# 5. FastAPI Dependency — get_db()
#    Usage in routes:
#      def my_route(db: Session = Depends(get_db)): ...
# ─────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────
# 6. CRUD Helpers
# ─────────────────────────────────────────
def create_incident(
    title: str,
    severity: str,
    root_cause: str,
    fix: str,
    postmortem: str,
    affected_components: str
) -> Incident:
    """Insert a new incident into the database and return it."""
    db = SessionLocal()
    try:
        incident = Incident(
            title=title,
            severity=severity,
            root_cause=root_cause,
            fix=fix,
            postmortem=postmortem,
            affected_components=affected_components,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident
    finally:
        db.close()


def get_all_incidents() -> list[Incident]:
    """Fetch all incidents ordered by newest first."""
    db = SessionLocal()
    try:
        return db.query(Incident).order_by(Incident.created_at.desc()).all()
    finally:
        db.close()


def get_incident_by_id(incident_id: int) -> Incident | None:
    """Fetch a single incident by its primary key."""
    db = SessionLocal()
    try:
        return db.query(Incident).filter(Incident.id == incident_id).first()
    finally:
        db.close()


def delete_incident(incident_id: int) -> bool:
    """Delete an incident by ID. Returns True if deleted, False if not found."""
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            db.delete(incident)
            db.commit()
            return True
        return False
    finally:
        db.close()


def get_db_status() -> dict:
    """Check database connectivity and return status info."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        count = SessionLocal().query(Incident).count()
        db_type = "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
        return {
            "status": "connected",
            "db_type": db_type,
            "total_incidents": count,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
