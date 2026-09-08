from pathlib import Path
from pypdf import PdfReader
from docx import Document
def extract_text(path):
    p=Path(path)
    if p.suffix.lower()==".pdf":
        return "\n".join((x.extract_text() or "") for x in PdfReader(str(p)).pages)
    if p.suffix.lower()==".docx":
        return "\n".join(x.text for x in Document(str(p)).paragraphs)
    raise ValueError("Only PDF and DOCX resumes are supported")
