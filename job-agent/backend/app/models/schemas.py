from typing import List, Optional
from pydantic import BaseModel


class ResumeProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    total_experience_years: Optional[float] = None
    skills: List[str] = []
    job_titles: List[str] = []
    preferred_roles: List[str] = []
    summary: Optional[str] = None
    raw_text: Optional[str] = None


class JobPosting(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = "Remote"
    source: str
    url: str
    posted_at: Optional[str] = None
    hours_ago: Optional[float] = None
    description: Optional[str] = ""
    tags: List[str] = []
    salary: Optional[str] = None
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    # LLM's best-effort estimate of the experience band this posting is looking
    # for, parsed from title/description. None means "couldn't tell" — such
    # jobs are kept rather than dropped so we don't over-filter on a guess.
    required_experience_min: Optional[float] = None
    required_experience_max: Optional[float] = None
    # True when hours_ago comes from a real timestamp (RemoteOK/WWR/Arbeitnow/
    # Adzuna) or a relative-age phrase actually parsed out of a Tavily-discovered
    # result (e.g. "3 days ago"). False means hours_ago is a guess or unknown --
    # Tavily's own recency filter is based on page last-crawled/updated time,
    # not the job's real posting date, so it cannot be trusted on its own.
    date_verified: bool = True


class JobSearchRequest(BaseModel):
    profile: ResumeProfile
    keywords: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    max_age_hours: Optional[int] = 24
    min_match_score: Optional[float] = 0
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    # When True (default), search-discovered jobs (LinkedIn/Indeed/Wellfound/
    # Naukri/country discovery) whose actual posting age can't be verified are
    # dropped rather than assumed fresh -- this is what fixes "I asked for 24h
    # and got a job from a month ago." Set False to see them anyway.
    require_verified_freshness: Optional[bool] = True


class JobSearchResponse(BaseModel):
    jobs: List[JobPosting]
    total_found: int
    total_after_filter: int


class JobExportRequest(BaseModel):
    jobs: List[JobPosting]
