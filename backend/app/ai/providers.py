import json
from openai import OpenAI
from ..core.config import settings
from ..schemas import FollowUpDecision, EvaluationOutput

class OpenAIProvider:
    def __init__(self):
        self.client=OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    def _require(self):
        if not self.client: raise RuntimeError("OPENAI_API_KEY is not configured")
    def generate_json(self, system, user, schema):
        self._require()
        r=self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            response_format={"type":"json_object"},
        )
        return schema.model_validate(json.loads(r.choices[0].message.content))
    def embed(self,text):
        self._require()
        return self.client.embeddings.create(model=settings.openai_embedding_model,input=text).data[0].embedding
    def plan(self, job, resume):
        return self.generate_json(
            "Create a job-focused interview plan. Use only supplied evidence. Return JSON.",
            f"JOB:{job}\nRESUME:{resume}\nReturn {{sections:[{{name,competency,weight,question_strategy}}]}}",
            PlanOutput)
    def followup(self, job, resume, recent, question, answer, remaining):
        return self.generate_json(
            "You are a professional neutral interviewer. Ask one question at a time. Do not give answers. Decide whether to follow up. Never use protected characteristics.",
            f"JOB:{job}\nRESUME:{resume}\nRECENT:{recent}\nQUESTION:{question}\nANSWER:{answer}\nTIME_REMAINING:{remaining}",
            FollowUpDecision)
    def evaluate(self, job, resume, transcript, answers, competencies):
        return self.generate_json(
            "Evaluate only job-related evidence. Never infer protected traits or appearance. Every important claim needs evidence. Recruiter makes final decisions.",
            f"JOB:{job}\nRESUME:{resume}\nCOMPETENCIES:{competencies}\nTRANSCRIPT:{transcript}\nANSWERS:{answers}",
            EvaluationOutput)

from pydantic import BaseModel
class Section(BaseModel):
    name:str
    competency:str
    weight:float
    question_strategy:str
class PlanOutput(BaseModel):
    sections:list[Section]
