from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.observability import init_langfuse, is_enabled
from app.api.routes import resume, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_langfuse()
    yield


app = FastAPI(
    title="Remote Job Agent API",
    description="Uploads a resume, extracts profile info with an LLM, and finds "
                 "fresh remote job postings matched to that profile.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(jobs.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "langfuse_monitoring": is_enabled()}
