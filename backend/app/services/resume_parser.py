"""
Extracts raw text from an uploaded resume (PDF/DOCX/TXT) and uses the Groq LLM
(via LangChain) to turn it into a structured ResumeProfile.
"""
import json
import re
from io import BytesIO

import pdfplumber
from docx import Document
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.observability import get_langfuse_handler
from app.models.schemas import ResumeProfile


def extract_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)
    elif lower.endswith(".docx"):
        doc = Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return file_bytes.decode("utf-8", errors="ignore")


def _get_llm():
    return ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)


EXTRACTION_PROMPT = """You are a resume parser. Given raw resume text, extract structured
information and respond with ONLY valid JSON (no markdown fences, no commentary) matching
this exact schema:

{
  "name": string or null,
  "email": string or null,
  "phone": string or null,
  "total_experience_years": number or null,
  "skills": [string],
  "job_titles": [string],
  "preferred_roles": [string, up to 5 likely job titles this person should search for],
  "summary": string (2-3 sentence professional summary)
}

Rules:
- total_experience_years should be your best numeric estimate based on work history dates.
- skills should be a deduplicated flat list of technical + relevant soft skills.
- preferred_roles should be realistic job titles matching this candidate's seniority/skills,
  useful as search queries on job boards.
"""


def _safe_json_extract(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def parse_resume(filename: str, file_bytes: bytes) -> ResumeProfile:
    raw_text = extract_text(filename, file_bytes)
    if not raw_text.strip():
        raise ValueError("Could not extract any text from the uploaded resume.")

    llm = _get_llm()
    config = {"run_name": "resume-extraction"}
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    response = llm.invoke(
        [
            SystemMessage(content=EXTRACTION_PROMPT),
            HumanMessage(content=raw_text[:12000]),
        ],
        config=config,
    )

    try:
        data = _safe_json_extract(response.content)
    except Exception:
        data = {}

    return ResumeProfile(
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        total_experience_years=data.get("total_experience_years"),
        skills=data.get("skills", []) or [],
        job_titles=data.get("job_titles", []) or [],
        preferred_roles=data.get("preferred_roles", []) or [],
        summary=data.get("summary"),
        raw_text=raw_text[:5000],
    )
