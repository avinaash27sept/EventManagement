from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

DB_PATH = "sqlite:///workshop_manager.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Event(Base):
    __tablename__ = "workshops"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    organizer_pdf = Column(String, nullable=True)
    registration_form = Column(String, nullable=True)
    organizing_department = Column(String, nullable=True)
    organizer_name = Column(String, nullable=True)


class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    institute = Column(String, nullable=True)
    department = Column(String, nullable=True)
    contact_no = Column(String, nullable=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    score = Column(Integer, nullable=True)
    certificate_sent = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    # best-effort: ensure new columns and table exist for older DBs
    try:
        import sqlite3
        db_file = DB_PATH.replace('sqlite:///', '')
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            # Ensure workshops has new columns
            cur.execute("PRAGMA table_info(workshops)")
            cols = [row[1] for row in cur.fetchall()]
            if "registration_form" not in cols:
                try:
                    cur.execute("ALTER TABLE workshops ADD COLUMN registration_form TEXT")
                except Exception:
                    pass
            if "organizing_department" not in cols:
                try:
                    cur.execute("ALTER TABLE workshops ADD COLUMN organizing_department TEXT")
                except Exception:
                    pass
            if "organizer_name" not in cols:
                try:
                    cur.execute("ALTER TABLE workshops ADD COLUMN organizer_name TEXT")
                except Exception:
                    pass
            conn.commit()
            # Ensure registrations table exists
            cur.execute("CREATE TABLE IF NOT EXISTS registrations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, institute TEXT, department TEXT, contact_no TEXT, workshop_id INTEGER NOT NULL, registered_at DATETIME, score INTEGER, certificate_sent BOOLEAN)")
            conn.commit()
            cur.close()
            conn.close()
    except Exception:
        # best-effort only
        pass


def get_session():
    return SessionLocal()
