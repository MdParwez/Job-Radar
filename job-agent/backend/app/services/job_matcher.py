"""
Scores each job against the candidate's resume profile using the Groq LLM, and
also has the LLM estimate the experience band ("required_experience_min/max")
each posting is looking for, parsed from its title/description.

Falls back to a simple keyword-overlap heuristic if the LLM call fails (or no
Groq key is configured), so the app never breaks just because scoring hiccups
-- it just becomes less precise.

Batches are scored CONCURRENTLY via `llm.ainvoke()` + asyncio.gather, not one
at a time with the blocking `llm.invoke()`. With e.g. 60 jobs across 4 batches,
sequential invoke() calls meant paying for 4x a single call's latency; gathering
them concurrently means paying for roughly 1x (bounded by Groq's own rate limit).
"""
import asyncio
import json
import re
from typing import List

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.observability import get_langfuse_handler
from app.models.schemas import JobPosting, ResumeProfile

SCORING_PROMPT = """You are a strict job-matching assistant for a candidate with a specific
technical domain. Given a candidate profile and a batch of job postings, for EACH job return:
  - score: 0-100 fit score
  - reason: one-sentence reason
  - min_years / max_years: your best-effort estimate of the years-of-experience band this
    posting is looking for, based on its title/description (e.g. "Senior" implies ~5-8,
    "Mid-level" implies ~3-5, an explicit "2+ years" implies min_years=2). Use null for
    either value if you genuinely cannot tell.

Respond with ONLY a JSON array, no markdown, in this exact shape:
[{"id": "<job id>", "score": <0-100>, "reason": "<short reason>", "min_years": <number or null>, "max_years": <number or null>}, ...]

Scoring rules (apply strictly):
- Domain match matters more than anything else. If the job's core discipline does not
  match the candidate's field (e.g. candidate is a software/AI engineer but the job is
  sales, marketing, finance, customer support, or another unrelated discipline), score
  it below 30 regardless of any surface keyword overlap.
- Within the same domain, score higher for stronger skill/tech-stack overlap and a
  seniority level appropriate to the candidate's years of experience.
- Do not inflate scores to be polite. A weak or off-domain match should score low.
"""

# Bounds how many Groq calls run at once, so a big result set doesn't blow
# through rate limits even though batches now run concurrently.
_SCORING_CONCURRENCY = asyncio.Semaphore(4)


def _heuristic_score(job: JobPosting, profile: ResumeProfile) -> float:
    text = f"{job.title} {job.description} {' '.join(job.tags)}".lower()
    skills = [s.lower() for s in profile.skills]
    if not skills:
        return 50.0
    hits = sum(1 for s in skills if s in text)
    # Low floor (10, not 40) so jobs with near-zero skill overlap actually fall
    # below a 70% threshold instead of always clearing it.
    return min(100.0, 10 + (hits / max(len(skills), 1)) * 90)


async def _score_batch(llm, batch, candidate_summary, batch_index, langfuse_handler):
    job_lines = "\n".join(
        f'- id: {j.id} | title: {j.title} | company: {j.company} | tags: {", ".join(j.tags)} | desc: {(j.description or "")[:300]}'
        for j in batch
    )
    config = {"run_name": f"job-scoring-batch-{batch_index}"}
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    async with _SCORING_CONCURRENCY:
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=SCORING_PROMPT),
                    HumanMessage(content=f"CANDIDATE:\n{candidate_summary}\n\nJOBS:\n{job_lines}"),
                ],
                config=config,
            )
            text = response.content.strip()
            text = re.sub(r"^```(json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
            match = re.search(r"\[.*\]", text, re.DOTALL)
            scores = json.loads(match.group(0) if match else text)
            return {s["id"]: s for s in scores}
        except Exception:
            return {}


async def score_jobs(jobs: List[JobPosting], profile: ResumeProfile) -> List[JobPosting]:
    if not jobs:
        return jobs

    if not settings.groq_api_key:
        for job in jobs:
            job.match_score = round(_heuristic_score(job, profile), 1)
            job.match_reason = "Heuristic keyword match (no LLM key configured)."
            # Heuristic mode can't reliably infer required experience; leave
            # unknown so experience filtering doesn't wrongly drop these.
        return jobs

    llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)

    candidate_summary = (
        f"Experience: {profile.total_experience_years} years\n"
        f"Skills: {', '.join(profile.skills[:40])}\n"
        f"Preferred roles: {', '.join(profile.preferred_roles)}\n"
        f"Summary: {profile.summary}"
    )

    langfuse_handler = get_langfuse_handler()

    batch_size = 15
    batches = [jobs[i:i + batch_size] for i in range(0, len(jobs), batch_size)]

    score_maps = await asyncio.gather(*(
        _score_batch(llm, batch, candidate_summary, idx, langfuse_handler)
        for idx, batch in enumerate(batches)
    ))

    scored_jobs: List[JobPosting] = []
    for batch, score_map in zip(batches, score_maps):
        for job in batch:
            if job.id in score_map:
                entry = score_map[job.id]
                job.match_score = float(entry.get("score", 50))
                job.match_reason = entry.get("reason", "")
                job.required_experience_min = entry.get("min_years")
                job.required_experience_max = entry.get("max_years")
            else:
                job.match_score = round(_heuristic_score(job, profile), 1)
                job.match_reason = "Heuristic fallback (LLM scoring unavailable for this job)."
            scored_jobs.append(job)

    scored_jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
    return scored_jobs
