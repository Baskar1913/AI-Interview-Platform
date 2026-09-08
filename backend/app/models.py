import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(20), index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Job(Base):
    __tablename__="jobs"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    recruiter_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str]=mapped_column(String(200))
    description: Mapped[str]=mapped_column(Text)
    experience_level: Mapped[str]=mapped_column(String(50))
    required_skills: Mapped[list]=mapped_column(JSON, default=list)
    preferred_skills: Mapped[list]=mapped_column(JSON, default=list)
    interview_type: Mapped[str]=mapped_column(String(30), default="Technical")
    duration_minutes: Mapped[int]=mapped_column(Integer, default=30)
    difficulty: Mapped[str]=mapped_column(String(30), default="Medium")
    competencies: Mapped[list]=mapped_column(JSON, default=list)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Candidate(Base):
    __tablename__="candidates"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    recruiter_id: Mapped[str]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255), index=True)
    phone: Mapped[str|None]=mapped_column(String(40), nullable=True)
    resume_path: Mapped[str|None]=mapped_column(String(500), nullable=True)
    resume_text: Mapped[str]=mapped_column(Text, default="")
    profile: Mapped[dict]=mapped_column(JSON, default=dict)

class Interview(Base):
    __tablename__="interviews"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str]=mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[str]=mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    duration_minutes: Mapped[int]=mapped_column(Integer, default=30)
    recording_enabled: Mapped[bool]=mapped_column(Boolean, default=True)
    status: Mapped[str]=mapped_column(String(40), default="READY", index=True)
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    current_section: Mapped[str]=mapped_column(String(100), default="Introduction")
    current_question: Mapped[str]=mapped_column(Text, default="")
    question_number: Mapped[int]=mapped_column(Integer, default=0)
    plan: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Answer(Base):
    __tablename__="answers"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    question: Mapped[str]=mapped_column(Text)
    text: Mapped[str]=mapped_column(Text)
    score: Mapped[float|None]=mapped_column(Float, nullable=True)
    evidence: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Transcript(Base):
    __tablename__="transcripts"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    speaker: Mapped[str]=mapped_column(String(20))
    text: Mapped[str]=mapped_column(Text)
    timestamp_start: Mapped[float]=mapped_column(Float, default=0)
    timestamp_end: Mapped[float]=mapped_column(Float, default=0)

class Evaluation(Base):
    __tablename__="evaluations"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), unique=True)
    overall_score: Mapped[float]=mapped_column(Float, default=0)
    competencies: Mapped[list]=mapped_column(JSON, default=list)
    strengths: Mapped[list]=mapped_column(JSON, default=list)
    gaps: Mapped[list]=mapped_column(JSON, default=list)
    evidence: Mapped[list]=mapped_column(JSON, default=list)
    confidence: Mapped[float]=mapped_column(Float, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Recording(Base):
    __tablename__="recordings"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), unique=True)
    file_path: Mapped[str]=mapped_column(String(500))
    duration: Mapped[float]=mapped_column(Float, default=0)
    file_size: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Report(Base):
    __tablename__="reports"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), unique=True)
    content: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class InterviewEvent(Base):
    __tablename__="interview_events"
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    interview_id: Mapped[str]=mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    event: Mapped[str]=mapped_column(String(60))
    payload: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
