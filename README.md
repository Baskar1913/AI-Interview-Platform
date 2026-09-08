# InterviewAI — Local MVP

A recruiter + candidate AI interview workspace built with React/Vite, FastAPI, PostgreSQL, OpenAI and ElevenLabs.

## Local services
- PostgreSQL: `localhost:5432`, database `ai_interview`
- Qdrant: `localhost:6333`
- FastAPI: `http://127.0.0.1:8000`
- React/Vite: `http://localhost:5173`

## Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env with your database, OpenAI and ElevenLabs credentials
python -m app.seed
uvicorn app.main:app --reload
```
Health: `http://127.0.0.1:8000/health`
Swagger: `http://127.0.0.1:8000/docs`

## Frontend
Open a second PowerShell:
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

## Demo accounts
- Recruiter: `demo-recruiter@example.com` / `Demo123!`
- Candidate: `demo-candidate@example.com` / `Demo123!`

## Recruiter workflow
1. Create a job. Required skills and interview duration are intentionally blank; enter the real requirements.
2. Add a candidate.
3. The system creates a candidate login and shows a temporary password once.
4. Upload the candidate PDF/DOCX resume.
5. Assign an interview only after the resume is ready.
6. Review candidate, job, transcript, recording and AI evaluation.

## Candidate workflow
1. Sign in using the recruiter-provided credentials.
2. Open the assigned interview.
3. Run camera/microphone/speaker checks.
4. Enter the dedicated fullscreen interview room.
5. The AI question is shown on screen while ElevenLabs speaks it.
6. Answer by voice (Chrome SpeechRecognition) or text, then submit.
7. The backend uses OpenAI to choose the next follow-up/question and stores the transcript.

The interview room uses browser MediaRecorder for a local WebM recording and browser speech recognition for voice answers. ElevenLabs is the TTS provider; if it is temporarily unavailable, browser speech synthesis is used as a fallback so the interview UI remains testable.
