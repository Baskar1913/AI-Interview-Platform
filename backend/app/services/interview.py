from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ..models import Interview, Job, Candidate, Answer, Transcript, Evaluation, Report
from ..ai.providers import OpenAIProvider

class InterviewService:
    def __init__(self,db): self.db=db; self.ai=OpenAIProvider()
    def start(self,i):
        if i.status not in ("READY","CREATED"): raise ValueError("Interview cannot be started")
        now=datetime.now(timezone.utc); i.status="INTRODUCTION"; i.started_at=now; i.deadline_at=now+timedelta(minutes=i.duration_minutes)
        self.db.flush(); return i
    def initial_question(self,i):
        job=self.db.get(Job,i.job_id); cand=self.db.get(Candidate,i.candidate_id)
        if self.ai.client:
            plan=self.ai.plan({"title":job.title,"description":job.description,"skills":job.required_skills},cand.resume_text)
            i.plan=plan.model_dump()
            sec=plan.sections[0]
            q=f"Tell me about your recent experience relevant to {sec.competency}."
        else:
            raise RuntimeError("OpenAI is not configured; AI interview generation is unavailable")
        i.status="QUESTIONING"; i.current_section=sec.name; i.current_question=q; i.question_number=1
        self.db.add(Transcript(interview_id=i.id,speaker="AI",text=q))
        self.db.commit(); return q
    def answer(self,i,text):
        if i.deadline_at and datetime.now(timezone.utc)>i.deadline_at: i.status="EXPIRED"; self.db.commit(); raise ValueError("Interview expired")
        q=i.current_question
        self.db.add(Answer(interview_id=i.id,question=q,text=text))
        self.db.add(Transcript(interview_id=i.id,speaker="Candidate",text=text))
        job=self.db.get(Job,i.job_id); cand=self.db.get(Candidate,i.candidate_id)
        recent=[{"q":a.question,"a":a.text} for a in self.db.query(Answer).filter(Answer.interview_id==i.id).order_by(Answer.created_at.desc()).limit(5)]
        remaining=max(0,int((i.deadline_at-datetime.now(timezone.utc)).total_seconds())) if i.deadline_at else 0
        d=self.ai.followup({"title":job.title,"description":job.description,"skills":job.required_skills},cand.resume_text,recent,q,text,remaining)
        if d.decision in ("FOLLOW_UP","CLARIFICATION") and d.question:
            nq=d.question
        else:
            sections=i.plan.get("sections",[])
            idx=min(i.question_number, max(0,len(sections)-1))
            sec=sections[idx] if sections else {"name":"Next topic","competency":"Problem Solving"}
            nq=f"How would you demonstrate strong {sec.get('competency','problem solving')} in this role?"
        i.question_number += 1; i.current_question=nq; i.current_section=d.topic or i.current_section; i.status="QUESTIONING"
        self.db.add(Transcript(interview_id=i.id,speaker="AI",text=nq))
        self.db.commit()
        return {"decision":d.decision,"question":nq}
    def complete(self,i):
        i.status="COMPLETED"; self.db.commit(); return i
    def evaluate(self,i):
        job=self.db.get(Job,i.job_id); cand=self.db.get(Candidate,i.candidate_id)
        answers=self.db.query(Answer).filter(Answer.interview_id==i.id).all()
        tx=self.db.query(Transcript).filter(Transcript.interview_id==i.id).all()
        out=self.ai.evaluate({"title":job.title,"description":job.description,"skills":job.required_skills},cand.resume_text,[{"speaker":x.speaker,"text":x.text} for x in tx],[{"q":x.question,"a":x.text} for x in answers],job.competencies)
        ev=self.db.query(Evaluation).filter(Evaluation.interview_id==i.id).first()
        values=out.model_dump(exclude={"summary"})
        if ev:
            for k,v in values.items(): setattr(ev,k,v)
        else:
            ev=Evaluation(interview_id=i.id,**values); self.db.add(ev)
        report=self.db.query(Report).filter(Report.interview_id==i.id).first()
        content={"summary":out.summary,"overall_score":out.overall_score,"competencies":out.competencies,"strengths":out.strengths,"gaps":out.gaps,"evidence":out.evidence,"confidence":out.confidence}
        if report: report.content=content
        else: report=Report(interview_id=i.id,content=content); self.db.add(report)
        self.db.commit()
        return ev,report
