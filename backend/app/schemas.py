from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class Register(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["recruiter", "candidate"]

class Login(BaseModel):
    email: EmailStr
    password: str

class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)
    experience_level: str = "Mid"
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    interview_type: str = "Technical"
    duration_minutes: int = Field(ge=5, le=180)
    difficulty: str = "Medium"
    competencies: list[dict] = []

class JobUpdate(JobCreate):
    pass

class CandidateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None

class CandidateUpdate(CandidateCreate):
    pass

class InterviewCreate(BaseModel):
    job_id: str
    candidate_id: str
    duration_minutes: int | None = Field(default=None, ge=5, le=180)
    recording_enabled: bool = True

class InterviewUpdate(BaseModel):
    duration_minutes: int | None = Field(default=None, ge=5, le=180)
    recording_enabled: bool | None = None

class AnswerSubmit(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

class FollowUpDecision(BaseModel):
    decision: Literal["FOLLOW_UP", "NEXT_QUESTION", "CLARIFICATION", "RETRY", "SKIP"]
    reason: str
    topic: str
    difficulty: str
    question: str | None = None

class EvaluationOutput(BaseModel):
    overall_score: float
    competencies: list[dict]
    strengths: list[str]
    gaps: list[str]
    evidence: list[str]
    confidence: float
    summary: str
