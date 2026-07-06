from fastapi import APIRouter, UploadFile, File, HTTPException
import asyncio

from app.models.schemas import ResumeProfile
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/api/resume", tags=["resume"])

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt")


@router.post("/upload", response_model=ResumeProfile)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Please upload a PDF, DOCX, or TXT resume.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        # parse_resume does blocking PDF/DOCX extraction + a synchronous Groq
        # call internally. Running it in a thread keeps the event loop free
        # for other requests (like a concurrent job search) while it works.
        profile = await asyncio.to_thread(parse_resume, file.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

    return profile
