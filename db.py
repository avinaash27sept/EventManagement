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
    feedback_enabled = Column(Boolean, default=False)


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
    confirmation_sent = Column(Boolean, default=False)


class EmailQueue(Base):
    __tablename__ = "email_queue"
    id = Column(Integer, primary_key=True, index=True)
    to_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    attachments = Column(Text, nullable=True)  # JSON-encoded list of file paths
    registration_id = Column(Integer, nullable=True)
    attempts = Column(Integer, default=0)
    next_attempt = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False)
    email = Column(String, nullable=True)
    q1 = Column(Integer, nullable=True)
    q2 = Column(Integer, nullable=True)
    q3 = Column(Integer, nullable=True)
    q4 = Column(Integer, nullable=True)
    q5 = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False)
    email = Column(String, nullable=False)
    answers = Column(Text, nullable=True)  # JSON-encoded answers
    score = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)


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
            # ensure feedback_enabled column exists
            if "feedback_enabled" not in cols:
                try:
                    cur.execute("ALTER TABLE workshops ADD COLUMN feedback_enabled BOOLEAN DEFAULT 0")
                except Exception:
                    pass
            conn.commit()
            # Ensure registrations table exists
            cur.execute("CREATE TABLE IF NOT EXISTS registrations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, institute TEXT, department TEXT, contact_no TEXT, workshop_id INTEGER NOT NULL, registered_at DATETIME, score INTEGER, certificate_sent BOOLEAN, confirmation_sent BOOLEAN)")
            conn.commit()
            # Ensure registrations has confirmation_sent column
            cur.execute("PRAGMA table_info(registrations)")
            reg_cols = [row[1] for row in cur.fetchall()]
            if "confirmation_sent" not in reg_cols:
                try:
                    cur.execute("ALTER TABLE registrations ADD COLUMN confirmation_sent BOOLEAN")
                except Exception:
                    pass
            conn.commit()
            # Ensure email_queue table exists
            cur.execute('''CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY,
                to_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT,
                attachments TEXT,
                registration_id INTEGER,
                attempts INTEGER DEFAULT 0,
                next_attempt DATETIME,
                last_error TEXT,
                created_at DATETIME
            )''')
            conn.commit()
            # Ensure feedback table exists
            cur.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                workshop_id INTEGER NOT NULL,
                email TEXT,
                q1 INTEGER,
                q2 INTEGER,
                q3 INTEGER,
                q4 INTEGER,
                q5 INTEGER,
                comments TEXT,
                submitted_at DATETIME
            )''')
            conn.commit()
            # Ensure feedback table has email column (for older DBs)
            cur.execute("PRAGMA table_info(feedback)")
            fb_cols = [row[1] for row in cur.fetchall()]
            if "email" not in fb_cols:
                try:
                    cur.execute("ALTER TABLE feedback ADD COLUMN email TEXT")
                except Exception:
                    pass
            conn.commit()
            # Ensure quiz_submissions table exists
            cur.execute('''CREATE TABLE IF NOT EXISTS quiz_submissions (
                id INTEGER PRIMARY KEY,
                workshop_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                answers TEXT,
                score INTEGER,
                submitted_at DATETIME
            )''')
            conn.commit()
            cur.close()
            conn.close()
    except Exception:
        # best-effort only
        pass


def get_session():
    return SessionLocal()
