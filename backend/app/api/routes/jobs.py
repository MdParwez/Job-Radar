from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.models.schemas import JobSearchRequest, JobSearchResponse, JobExportRequest
from app.agents.langgraph_agent import run_job_agent
from app.services.excel_export import build_jobs_workbook, export_filename

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

DEFAULT_SOURCES = ["remoteok", "weworkremotely", "linkedin", "indeed", "wellfound", "arbeitnow"]


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(payload: JobSearchRequest):
    sources = payload.sources or DEFAULT_SOURCES
    max_age = payload.max_age_hours or settings.job_max_age_hours

    try:
        state = await run_job_agent(
            profile=payload.profile,
            sources=sources,
            max_age_hours=max_age,
            keywords=payload.keywords,
            min_match_score=payload.min_match_score or 0,
            min_experience_years=payload.min_experience_years,
            max_experience_years=payload.max_experience_years,
            require_verified_freshness=payload.require_verified_freshness if payload.require_verified_freshness is not None else True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search failed: {e}")

    return JobSearchResponse(
        jobs=state["final_jobs"],
        total_found=len(state["raw_jobs"]),
        total_after_filter=len(state["filtered_jobs"]),
    )


@router.post("/export")
async def export_jobs(payload: JobExportRequest):
    if not payload.jobs:
        raise HTTPException(status_code=400, detail="No jobs to export.")

    buffer = build_jobs_workbook(payload.jobs)
    filename = export_filename()

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
