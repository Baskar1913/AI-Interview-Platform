from .database import Base,engine,SessionLocal
from .models import User,Job,Candidate,Interview
from .core.security import hash_password
Base.metadata.create_all(engine)
db=SessionLocal()
r=db.query(User).filter(User.email=="demo-recruiter@example.com").first()
if not r:
    r=User(name="Demo Recruiter",email="demo-recruiter@example.com",password_hash=hash_password("Demo123!"),role="recruiter"); db.add(r); db.flush()
cuser=db.query(User).filter(User.email=="demo-candidate@example.com").first()
if not cuser:
    cuser=User(name="Demo Candidate",email="demo-candidate@example.com",password_hash=hash_password("Demo123!"),role="candidate"); db.add(cuser); db.flush()
j=db.query(Job).filter(Job.recruiter_id==r.id).first()
if not j:
    j=Job(recruiter_id=r.id,title="Python Backend Developer",description="Build APIs and backend services with Python.",experience_level="Mid",required_skills=["Python","FastAPI","PostgreSQL","REST API"],preferred_skills=["Docker"],duration_minutes=30,difficulty="Medium",competencies=[{"name":"Python","weight":25},{"name":"FastAPI","weight":25},{"name":"PostgreSQL","weight":20},{"name":"REST APIs","weight":15},{"name":"Problem Solving","weight":15}]); db.add(j); db.flush()
c=db.query(Candidate).filter(Candidate.email=="demo-candidate@example.com").first()
if not c:
    c=Candidate(recruiter_id=r.id,user_id=cuser.id,name="Demo Candidate",email=cuser.email,resume_text="Python developer with FastAPI and PostgreSQL project experience."); db.add(c); db.flush()
if not db.query(Interview).filter(Interview.candidate_id==c.id).first():
    db.add(Interview(job_id=j.id,candidate_id=c.id,duration_minutes=30,recording_enabled=True))
db.commit(); db.close(); print("Seed complete")
