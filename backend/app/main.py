from datetime import datetime, timezone
import secrets
import string
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base, engine, get_db
from .models import User, Job, Candidate, Interview, Transcript, Evaluation, Report, Recording, Answer
from .schemas import *
from .core.config import settings
from .core.security import hash_password, verify_password, create_token, current_user, require_role
from .services.resume import extract_text
from .services.interview import InterviewService
from .storage.local import LocalFileStorage
from .voice.elevenlabs import ElevenLabsProvider

Base.metadata.create_all(engine)
app = FastAPI(title="AI Interview Platform", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
storage = LocalFileStorage()
voice = ElevenLabsProvider()


def clean_skills(values):
    return list(dict.fromkeys([str(x).strip() for x in (values or []) if str(x).strip()]))


def serialize_job(j):
    return {
        "id": j.id, "title": j.title, "description": j.description,
        "experience_level": j.experience_level, "required_skills": j.required_skills or [],
        "preferred_skills": j.preferred_skills or [], "interview_type": j.interview_type,
        "duration_minutes": j.duration_minutes, "difficulty": j.difficulty,
        "competencies": j.competencies or [], "created_at": j.created_at,
    }


def serialize_candidate(c, db):
    count = db.query(func.count(Interview.id)).filter(Interview.candidate_id == c.id).scalar() or 0
    return {
        "id": c.id, "name": c.name, "email": c.email, "phone": c.phone,
        "resume_path": c.resume_path, "has_resume": bool((c.resume_text or "").strip()),
        "resume_text_preview": (c.resume_text or "")[:500], "interview_count": count,
        "user_id": c.user_id,
    }


def serialize_interview(i, db, include_candidate_resume=False):
    j = db.get(Job, i.job_id); c = db.get(Candidate, i.candidate_id)
    e = db.query(Evaluation).filter(Evaluation.interview_id == i.id).first()
    r = db.query(Recording).filter(Recording.interview_id == i.id).first()
    payload = {
        "id": i.id, "status": i.status, "duration_minutes": i.duration_minutes,
        "recording_enabled": i.recording_enabled, "started_at": i.started_at,
        "deadline_at": i.deadline_at, "current_section": i.current_section,
        "current_question": i.current_question, "question_number": i.question_number,
        "created_at": i.created_at,
        "job": serialize_job(j) if j else None,
        "candidate": {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "has_resume": bool((c.resume_text or "").strip())} if c else None,
        "evaluation": {"overall_score": e.overall_score, "confidence": e.confidence} if e else None,
        "recording_available": bool(r),
    }
    if include_candidate_resume and c:
        payload["candidate"]["resume_text"] = c.resume_text or ""
    return payload


def get_interview(id, u, db):
    i = db.get(Interview, id)
    if not i:
        raise HTTPException(404, "Interview not found")
    c = db.get(Candidate, i.candidate_id); j = db.get(Job, i.job_id)
    if not c or not j:
        raise HTTPException(404, "Interview data is incomplete")
    if u.role == "recruiter" and j.recruiter_id != u.id:
        raise HTTPException(403, "Forbidden")
    if u.role == "candidate" and c.user_id != u.id:
        raise HTTPException(403, "Forbidden")
    return i


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "@#%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI Interview Platform", "ai": {"openai": bool(settings.openai_api_key), "elevenlabs": bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id)}, "qdrant": bool(settings.qdrant_url)}


@app.post("/api/v1/auth/register")
def register(x: Register, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == x.email).first():
        raise HTTPException(400, "Email already registered")
    u = User(name=x.name, email=x.email, password_hash=hash_password(x.password), role=x.role)
    db.add(u); db.commit(); db.refresh(u)
    return {"access_token": create_token(u), "user": {"id": u.id, "name": u.name, "email": u.email, "role": u.role}}


@app.post("/api/v1/auth/login")
def login(x: Login, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == x.email).first()
    if not u or not verify_password(x.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(u), "user": {"id": u.id, "name": u.name, "email": u.email, "role": u.role}}


@app.get("/api/v1/users/me")
def me(u=Depends(current_user)):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


# ---------------- Jobs CRUD ----------------
@app.post("/api/v1/jobs")
def create_job(x: JobCreate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    data = x.model_dump(); data["required_skills"] = clean_skills(data["required_skills"]); data["preferred_skills"] = clean_skills(data["preferred_skills"])
    if not data["required_skills"]:
        raise HTTPException(400, "Add at least one required skill")
    if not data["competencies"]:
        data["competencies"] = [{"name": s, "weight": round(100 / len(data["required_skills"]), 2)} for s in data["required_skills"]]
    j = Job(recruiter_id=u.id, **data); db.add(j); db.commit(); db.refresh(j)
    return serialize_job(j)


@app.get("/api/v1/jobs")
def jobs(u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    return [serialize_job(j) for j in db.query(Job).filter(Job.recruiter_id == u.id).order_by(Job.created_at.desc()).all()]


@app.get("/api/v1/jobs/{id}")
def job(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    j = db.get(Job, id)
    if not j or j.recruiter_id != u.id: raise HTTPException(404, "Job not found")
    return serialize_job(j)


@app.put("/api/v1/jobs/{id}")
def update_job(id: str, x: JobUpdate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    j = db.get(Job, id)
    if not j or j.recruiter_id != u.id: raise HTTPException(404, "Job not found")
    data = x.model_dump(); data["required_skills"] = clean_skills(data["required_skills"]); data["preferred_skills"] = clean_skills(data["preferred_skills"])
    if not data["required_skills"]: raise HTTPException(400, "Add at least one required skill")
    if not data["competencies"]: data["competencies"] = [{"name": s, "weight": round(100 / len(data["required_skills"]), 2)} for s in data["required_skills"]]
    for k, v in data.items(): setattr(j, k, v)
    db.commit(); db.refresh(j); return serialize_job(j)


@app.delete("/api/v1/jobs/{id}")
def delete_job(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    j = db.get(Job, id)
    if not j or j.recruiter_id != u.id: raise HTTPException(404, "Job not found")
    db.delete(j); db.commit(); return {"deleted": True, "id": id}


# ---------------- Candidates CRUD + account provisioning ----------------
@app.post("/api/v1/candidates")
def create_candidate(x: CandidateCreate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    if db.query(Candidate).filter(Candidate.recruiter_id == u.id, Candidate.email == x.email).first():
        raise HTTPException(409, "This candidate already exists")
    existing_user = db.query(User).filter(User.email == x.email).first()
    temp_password = generate_temp_password()
    if existing_user:
        if existing_user.role != "candidate": raise HTTPException(409, "Email belongs to another user role")
        candidate_user = existing_user
        # Do not reset an existing candidate's password.
        temp_password = None
    else:
        candidate_user = User(name=x.name, email=x.email, password_hash=hash_password(temp_password), role="candidate")
        db.add(candidate_user); db.flush()
    c = Candidate(recruiter_id=u.id, user_id=candidate_user.id, **x.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    result = serialize_candidate(c, db)
    result["temporary_password"] = temp_password
    result["login_email"] = candidate_user.email
    return result


@app.get("/api/v1/candidates")
def candidates(u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    return [serialize_candidate(c, db) for c in db.query(Candidate).filter(Candidate.recruiter_id == u.id).order_by(Candidate.name.asc()).all()]


@app.get("/api/v1/candidates/{id}")
def candidate(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    c = db.get(Candidate, id)
    if not c or c.recruiter_id != u.id: raise HTTPException(404, "Candidate not found")
    result = serialize_candidate(c, db)
    result["resume_text"] = c.resume_text or ""
    result["interviews"] = [serialize_interview(i, db) for i in db.query(Interview).filter(Interview.candidate_id == c.id).order_by(Interview.created_at.desc()).all()]
    return result


@app.put("/api/v1/candidates/{id}")
def update_candidate(id: str, x: CandidateUpdate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    c = db.get(Candidate, id)
    if not c or c.recruiter_id != u.id: raise HTTPException(404, "Candidate not found")
    if x.email != c.email:
        other = db.query(Candidate).filter(Candidate.recruiter_id == u.id, Candidate.email == x.email, Candidate.id != id).first()
        if other: raise HTTPException(409, "A candidate with that email already exists")
        if c.user_id:
            user = db.get(User, c.user_id)
            if user: user.email = x.email
    for k, v in x.model_dump().items(): setattr(c, k, v)
    db.commit(); db.refresh(c); return serialize_candidate(c, db)


@app.delete("/api/v1/candidates/{id}")
def delete_candidate(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    c = db.get(Candidate, id)
    if not c or c.recruiter_id != u.id: raise HTTPException(404, "Candidate not found")
    user_id = c.user_id; db.delete(c); db.flush()
    if user_id:
        user = db.get(User, user_id)
        if user and user.role == "candidate":
            db.delete(user)
    db.commit()
    return {"deleted": True, "id": id, "candidate_login_removed": bool(user_id)}


@app.post("/api/v1/candidates/{id}/reset-password")
def reset_candidate_password(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    c = db.get(Candidate, id)
    if not c or c.recruiter_id != u.id: raise HTTPException(404, "Candidate not found")
    user = db.get(User, c.user_id) if c.user_id else None
    if not user: raise HTTPException(400, "Candidate login account is missing")
    password = generate_temp_password(); user.password_hash = hash_password(password); db.commit()
    return {"login_email": user.email, "temporary_password": password}


@app.post("/api/v1/resumes/upload")
async def upload_resume(candidate_id: str, file: UploadFile = File(...), u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    c = db.get(Candidate, candidate_id)
    if not c or c.recruiter_id != u.id: raise HTTPException(404, "Candidate not found")
    if file.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(400, "Only PDF and DOCX are supported")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(400, "File too large; maximum is 10 MB")
    path = storage.save("resumes", file.filename, data); text = extract_text(path)
    if not text.strip(): raise HTTPException(400, "Could not extract text from the resume")
    c.resume_path = path; c.resume_text = text[:100000]; c.profile = {"raw_text_length": len(text), "filename": file.filename}
    db.commit(); return {"candidate_id": c.id, "path": path, "text_length": len(text), "has_resume": True}


# ---------------- Interviews CRUD ----------------
@app.post("/api/v1/interviews")
def create_interview(x: InterviewCreate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    j = db.get(Job, x.job_id); c = db.get(Candidate, x.candidate_id)
    if not j or j.recruiter_id != u.id or not c or c.recruiter_id != u.id: raise HTTPException(404, "Resource not found")
    if not (c.resume_text or "").strip(): raise HTTPException(400, "Upload a candidate resume before creating an interview")
    if db.query(Interview).filter(Interview.job_id == j.id, Interview.candidate_id == c.id, Interview.status.in_(["READY", "INTRODUCTION", "QUESTIONING"])).first():
        raise HTTPException(409, "This candidate already has an active interview for this job")
    i = Interview(job_id=j.id, candidate_id=c.id, duration_minutes=x.duration_minutes or j.duration_minutes, recording_enabled=x.recording_enabled)
    db.add(i); db.commit(); db.refresh(i); return serialize_interview(i, db)


@app.get("/api/v1/interviews")
def interviews(u=Depends(current_user), db: Session = Depends(get_db)):
    if u.role == "recruiter":
        ids = [j.id for j in db.query(Job).filter(Job.recruiter_id == u.id).all()]
        rows = db.query(Interview).filter(Interview.job_id.in_(ids)).order_by(Interview.created_at.desc()).all() if ids else []
        return [serialize_interview(i, db) for i in rows]
    cs = [c.id for c in db.query(Candidate).filter(Candidate.user_id == u.id).all()]
    rows = db.query(Interview).filter(Interview.candidate_id.in_(cs)).order_by(Interview.created_at.desc()).all() if cs else []
    return [serialize_interview(i, db) for i in rows]


@app.get("/api/v1/interviews/{id}")
def interview(id: str, u=Depends(current_user), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    return serialize_interview(i, db, include_candidate_resume=(u.role == "recruiter"))


@app.put("/api/v1/interviews/{id}")
def update_interview(id: str, x: InterviewUpdate, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if i.status not in ("READY", "CREATED"):
        raise HTTPException(400, "Only a ready interview can be edited")
    if x.duration_minutes is not None: i.duration_minutes = x.duration_minutes
    if x.recording_enabled is not None: i.recording_enabled = x.recording_enabled
    db.commit(); db.refresh(i); return serialize_interview(i, db)


@app.delete("/api/v1/interviews/{id}")
def delete_interview(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    i = get_interview(id, u, db); db.delete(i); db.commit(); return {"deleted": True, "id": id}


@app.post("/api/v1/interviews/{id}/start")
def start(id: str, u=Depends(current_user), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if u.role != "candidate":
        raise HTTPException(403, "Candidate access required")
    try:
        service = InterviewService(db)
        # Make start retry-safe. A previous AI/API failure may have left the
        # interview in INTRODUCTION; retry the question generation instead of
        # permanently blocking the candidate. If a question already exists,
        # return it rather than creating a duplicate question.
        if i.status in ("READY", "CREATED"):
            service.start(i)
        elif i.status == "QUESTIONING" and i.current_question:
            return {"question": i.current_question, "status": i.status, "deadline_at": i.deadline_at, "question_number": i.question_number, "section": i.current_section}
        elif i.status == "INTRODUCTION":
            if not i.deadline_at:
                service.start(i)
        else:
            raise ValueError(f"Interview cannot be started from status {i.status}")
        q = service.initial_question(i)
    except RuntimeError as e:
        db.rollback()
        raise HTTPException(503, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(503, f"Unable to prepare the interview: {e}")
    return {"question": q, "status": i.status, "deadline_at": i.deadline_at, "question_number": i.question_number, "section": i.current_section}


@app.post("/api/v1/interviews/{id}/answer")
def answer(id: str, x: AnswerSubmit, u=Depends(current_user), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if u.role != "candidate": raise HTTPException(403, "Candidate access required")
    try: return InterviewService(db).answer(i, x.text)
    except RuntimeError as e: raise HTTPException(503, str(e))
    except ValueError as e: raise HTTPException(400, str(e))


@app.post("/api/v1/interviews/{id}/complete")
def complete(id: str, u=Depends(current_user), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if u.role != "candidate": raise HTTPException(403, "Candidate access required")
    InterviewService(db).complete(i); return {"status": "COMPLETED"}


@app.post("/api/v1/interviews/{id}/recording")
async def recording(id: str, file: UploadFile = File(...), u=Depends(current_user), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if u.role != "candidate": raise HTTPException(403, "Candidate access required")
    data = await file.read(); path = storage.save("recordings", file.filename or "interview.webm", data)
    old = db.query(Recording).filter(Recording.interview_id == i.id).first()
    if old: db.delete(old)
    db.add(Recording(interview_id=i.id, file_path=path, file_size=len(data))); db.commit()
    return {"saved": True, "file_size": len(data)}


@app.get("/api/v1/interviews/{id}/recording")
def get_recording(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    i = get_interview(id, u, db); r = db.query(Recording).filter(Recording.interview_id == i.id).first()
    if not r: raise HTTPException(404, "Recording not available")
    path = Path(r.file_path)
    if not path.exists(): raise HTTPException(404, "Recording file not found")
    return FileResponse(path, media_type="video/webm", filename=path.name)


@app.post("/api/v1/interviews/{id}/speak")
async def speak(id: str, x: SpeakRequest, u=Depends(current_user), db: Session = Depends(get_db)):
    get_interview(id, u, db)
    if u.role != "candidate": raise HTTPException(403, "Candidate access required")
    try:
        audio = await voice.synthesize(x.text)
        return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
    except Exception as e:
        raise HTTPException(503, f"AI voice is unavailable: {e}")


@app.get("/api/v1/interviews/{id}/transcript")
def transcript(id: str, u=Depends(current_user), db: Session = Depends(get_db)):
    get_interview(id, u, db)
    return [{"speaker": x.speaker, "text": x.text, "timestamp_start": x.timestamp_start, "timestamp_end": x.timestamp_end} for x in db.query(Transcript).filter(Transcript.interview_id == id).order_by(Transcript.created_at.asc()).all()]


@app.get("/api/v1/interviews/{id}/evaluation")
def evaluation(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    get_interview(id, u, db); e = db.query(Evaluation).filter(Evaluation.interview_id == id).first()
    if not e: raise HTTPException(404, "Evaluation not generated")
    return e.__dict__


@app.get("/api/v1/interviews/{id}/report")
def report(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    get_interview(id, u, db); r = db.query(Report).filter(Report.interview_id == id).first()
    if not r: raise HTTPException(404, "Report not generated")
    return r.content


@app.post("/api/v1/interviews/{id}/evaluate")
def evaluate(id: str, u=Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    i = get_interview(id, u, db)
    if i.status != "COMPLETED": raise HTTPException(400, "Complete the interview before generating an evaluation")
    try:
        e, r = InterviewService(db).evaluate(i); return {"evaluation": e.__dict__, "report": r.content}
    except RuntimeError as ex: raise HTTPException(503, str(ex))


@app.websocket("/ws/interviews/{id}")
async def ws(id: str, websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008); return
    try:
        from jose import jwt, JWTError
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, data.get("sub"))
        if not user: raise JWTError()
        get_interview(id, user, db)
    except Exception:
        await websocket.close(code=1008); return
    await websocket.accept()
    try:
        await websocket.send_json({"event": "CONNECTED", "interview_id": id})
        while True:
            msg = await websocket.receive_json()
            await websocket.send_json({"event": "ACK", "payload": msg})
    except WebSocketDisconnect:
        pass
