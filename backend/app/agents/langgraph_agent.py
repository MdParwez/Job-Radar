"""
LangGraph pipeline that orchestrates the job-search agent:

  fetch_sources -> filter_by_freshness -> score_and_rank -> filter_by_criteria -> END

Each node is a plain function operating on a shared state dict, which keeps this
easy to extend (e.g. add a "dedupe_by_company" node, a "generate_cover_letter"
node, etc.) without touching the API layer.
"""
import asyncio
from typing import List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.core.observability import get_langfuse_handler
from app.models.schemas import JobPosting, ResumeProfile
from app.scrapers.remoteok import fetch_remoteok_jobs
from app.scrapers.weworkremotely import fetch_wwr_jobs
from app.scrapers.tavily_search import (
    fetch_via_tavily,
    fetch_country_jobs_via_tavily,
    COUNTRY_DISPLAY_NAMES,
)
from app.scrapers.arbeitnow import fetch_arbeitnow_jobs
from app.scrapers.adzuna import fetch_adzuna_jobs, ADZUNA_COUNTRY_CODES
from app.services.job_matcher import score_jobs


class AgentState(TypedDict):
    profile: ResumeProfile
    sources: List[str]
    max_age_hours: int
    keywords: List[str]
    min_match_score: float
    min_experience_years: Optional[float]
    max_experience_years: Optional[float]
    require_verified_freshness: bool
    raw_jobs: List[JobPosting]
    filtered_jobs: List[JobPosting]
    ranked_jobs: List[JobPosting]
    final_jobs: List[JobPosting]


async def _fetch_regional_country(country_key: str, roles: List[str], max_age_hours: int) -> List[JobPosting]:
    """Combines the official Adzuna API (where the country is covered) with
    Tavily's broader country-scoped discovery (for everything else), deduped
    by URL."""
    results = await asyncio.gather(
        fetch_adzuna_jobs(country_key, roles) if country_key in ADZUNA_COUNTRY_CODES else _empty(),
        fetch_country_jobs_via_tavily(country_key, roles, max_age_hours),
        return_exceptions=True,
    )
    combined: List[JobPosting] = []
    seen_urls = set()
    for r in results:
        if isinstance(r, Exception):
            continue
        for job in r:
            if job.url in seen_urls:
                continue
            seen_urls.add(job.url)
            combined.append(job)
    return combined


async def _empty() -> List[JobPosting]:
    return []


async def fetch_sources_node(state: AgentState) -> AgentState:
    sources = state["sources"]
    roles = state["profile"].preferred_roles or state["profile"].job_titles or ["software engineer"]
    keywords = state["keywords"] or [s.lower() for s in state["profile"].skills[:10]]
    max_age = state["max_age_hours"]

    tasks = []
    if "remoteok" in sources:
        tasks.append(fetch_remoteok_jobs(keywords))
    if "weworkremotely" in sources:
        tasks.append(fetch_wwr_jobs(keywords))
    if "linkedin" in sources:
        tasks.append(fetch_via_tavily("linkedin", roles, max_age))
    if "indeed" in sources:
        tasks.append(fetch_via_tavily("indeed", roles, max_age))
    if "wellfound" in sources:
        tasks.append(fetch_via_tavily("wellfound", roles, max_age))
    if "naukri" in sources:
        tasks.append(fetch_via_tavily("naukri", roles, max_age))
    if "arbeitnow" in sources:
        tasks.append(fetch_arbeitnow_jobs(keywords))

    # One task per requested country (Germany, Ireland, UK, Poland, Sweden,
    # Denmark, Brazil, Chile, Philippines, Malaysia, Indonesia, Japan, Australia)
    for country_key in COUNTRY_DISPLAY_NAMES:
        if country_key in sources:
            tasks.append(_fetch_regional_country(country_key, roles, max_age))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_jobs: List[JobPosting] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        all_jobs.extend(r)

    state["raw_jobs"] = all_jobs
    return state


def filter_by_freshness_node(state: AgentState) -> AgentState:
    max_age = state["max_age_hours"]
    require_verified = state.get("require_verified_freshness", True)
    fresh = []
    for job in state["raw_jobs"]:
        if job.hours_ago is None:
            # Unverified posting age (search-discovered result with no
            # extractable relative-age phrase). Tavily's own time_range
            # filter is based on page last-crawled/updated time, NOT the
            # job's actual posting date, so an unverified job cannot be
            # assumed fresh just because it passed that filter -- that
            # assumption was the root cause of "24h search" returning
            # month-old postings. Drop it unless the caller explicitly
            # opted into seeing unverified-date results.
            if not require_verified:
                fresh.append(job)
        elif job.hours_ago <= max_age:
            fresh.append(job)
    state["filtered_jobs"] = fresh
    return state


async def score_and_rank_node(state: AgentState) -> AgentState:
    state["ranked_jobs"] = await score_jobs(state["filtered_jobs"], state["profile"])
    return state


def _experience_overlaps(job: JobPosting, min_years: Optional[float], max_years: Optional[float]) -> bool:
    """True if the job's (LLM-estimated) required experience band overlaps the
    candidate's requested [min_years, max_years] window. If the job's band is
    unknown, or the candidate didn't specify a window, we keep the job rather
    than guess wrong and drop something relevant."""
    if min_years is None and max_years is None:
        return True
    if job.required_experience_min is None and job.required_experience_max is None:
        return True

    job_min = job.required_experience_min if job.required_experience_min is not None else 0
    job_max = job.required_experience_max if job.required_experience_max is not None else 999
    want_min = min_years if min_years is not None else 0
    want_max = max_years if max_years is not None else 999

    return job_min <= want_max and job_max >= want_min


def filter_by_criteria_node(state: AgentState) -> AgentState:
    min_score = state.get("min_match_score") or 0
    min_years = state.get("min_experience_years")
    max_years = state.get("max_experience_years")

    final = [
        job for job in state["ranked_jobs"]
        if (job.match_score or 0) >= min_score
        and _experience_overlaps(job, min_years, max_years)
    ]
    state["final_jobs"] = final
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("fetch_sources", fetch_sources_node)
    graph.add_node("filter_by_freshness", filter_by_freshness_node)
    graph.add_node("score_and_rank", score_and_rank_node)
    graph.add_node("filter_by_criteria", filter_by_criteria_node)

    graph.set_entry_point("fetch_sources")
    graph.add_edge("fetch_sources", "filter_by_freshness")
    graph.add_edge("filter_by_freshness", "score_and_rank")
    graph.add_edge("score_and_rank", "filter_by_criteria")
    graph.add_edge("filter_by_criteria", END)

    return graph.compile()


_compiled_graph = build_graph()


async def run_job_agent(
    profile: ResumeProfile,
    sources: List[str],
    max_age_hours: int = 24,
    keywords: List[str] | None = None,
    min_match_score: float = 0,
    min_experience_years: Optional[float] = None,
    max_experience_years: Optional[float] = None,
    require_verified_freshness: bool = True,
) -> AgentState:
    initial_state: AgentState = {
        "profile": profile,
        "sources": sources,
        "max_age_hours": max_age_hours,
        "keywords": keywords or [],
        "min_match_score": min_match_score,
        "min_experience_years": min_experience_years,
        "max_experience_years": max_experience_years,
        "require_verified_freshness": require_verified_freshness,
        "raw_jobs": [],
        "filtered_jobs": [],
        "ranked_jobs": [],
        "final_jobs": [],
    }
    config = {}
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
        config["run_name"] = "job-search-agent"

    final_state = await _compiled_graph.ainvoke(initial_state, config=config)
    return final_state
