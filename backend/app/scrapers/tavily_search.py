"""
LinkedIn and Indeed block scrapers aggressively and their ToS prohibit automated
scraping. Wellfound has no simple public API either. Instead of fighting anti-bot
systems, we use Tavily's search API (free tier) to discover *publicly indexed*
job postings on these domains, restricted to the last N hours, then link out to
the real listing. This is far more robust than a hand-rolled scraper and won't
break every time a site changes its HTML.

Uses AsyncTavilyClient (not the sync TavilyClient) so that calls actually run
concurrently under asyncio.gather instead of blocking the whole event loop for
each request's duration -- with the sync client, "concurrent" source fetches
were secretly serializing, which was the single biggest cause of search latency.
Each role query also runs concurrently (bounded by a semaphore) instead of in
a sequential for-loop.
"""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlparse

from tavily import AsyncTavilyClient

from app.core.config import settings
from app.models.schemas import JobPosting

SITE_MAP = {
    "linkedin": "linkedin.com/jobs",
    "indeed": "indeed.com",
    "wellfound": "wellfound.com",
    "naukri": "naukri.com",
}

# Countries with no clean free/public job-board API we could verify (unlike
# Arbeitnow for Germany/EU or Adzuna's officially-covered countries). For these
# we fall back to a broad, non-site-restricted search scoped to the country
# name itself, so results can come from whatever local boards Tavily has
# indexed (StepStone, Pracuj.pl, IrishJobs.ie, Arbetsformedlingen, JobStreet,
# Gupy, Seek, etc.) rather than guessing one specific portal per country.
COUNTRY_DISPLAY_NAMES = {
    "germany": "Germany",
    "ireland": "Ireland",
    "uk": "United Kingdom",
    "poland": "Poland",
    "sweden": "Sweden",
    "denmark": "Denmark",
    "brazil": "Brazil",
    "chile": "Chile",
    "philippines": "Philippines",
    "malaysia": "Malaysia",
    "indonesia": "Indonesia",
    "japan": "Japan",
    "australia": "Australia",
    # Middle East / GCC. Dubai and Abu Dhabi are emirates within the UAE, not
    # separate countries, so both are covered by the "uae" key.
    "uae": "United Arab Emirates (Dubai, Abu Dhabi)",
    "qatar": "Qatar",
    "saudi_arabia": "Saudi Arabia",
    "bahrain": "Bahrain",
    "kuwait": "Kuwait",
    "oman": "Oman",
}

# Caps how many Tavily calls run at once across this whole process. Keeps us
# a good API citizen and avoids hammering the free-tier rate limit, while
# still letting several role/source queries run genuinely in parallel instead
# of one-at-a-time.
_SEMAPHORE = asyncio.Semaphore(6)


def _guess_source(url: str) -> str:
    host = urlparse(url).netloc
    if "linkedin" in host:
        return "LinkedIn"
    if "indeed" in host:
        return "Indeed"
    if "wellfound" in host or "angel.co" in host:
        return "Wellfound"
    if "naukri" in host:
        return "Naukri"
    return host


# Matches the relative-age phrasing job boards commonly render, e.g.
# "Posted 3 days ago", "2 hours ago", "30+ days ago", "Just posted", "Today".
# This is the ONLY reliable freshness signal available for Tavily-discovered
# results, since Tavily's `results[]` schema has no published-date field at
# all, and its `time_range` filter is based on when the PAGE was last crawled
# or updated -- not when the specific job was posted. A stale job listing on
# a frequently-recrawled aggregator page can pass `time_range="day"` even
# though the job itself is a month old, which is exactly the bug this fixes.
_UNIT_MULTIPLIERS = {
    "hours?\\s+ago": 1,
    "days?\\s+ago": 24,
    "weeks?\\s+ago": 24 * 7,
    "months?\\s+ago": 24 * 30,
}


def _extract_hours_ago(text: str) -> Optional[float]:
    """Best-effort extraction of a relative posting age from free text.
    Returns None if no recognizable pattern is found -- callers must treat
    that as "unverified", not "fresh"."""
    if not text:
        return None

    if re.search(r"\bjust posted\b", text, re.I):
        return 0.0
    if re.search(r"\bposted today\b", text, re.I) or re.search(r"\btoday\b", text, re.I):
        return 1.0
    if re.search(r"\byesterday\b", text, re.I):
        return 24.0

    for unit_pattern, multiplier in _UNIT_MULTIPLIERS.items():
        match = re.search(rf"(\d+)\s*\+?\s*{unit_pattern}", text, re.I)
        if match:
            return float(match.group(1)) * multiplier

    return None


def _jobs_from_results(results: dict, role: str, location_label: Optional[str] = None) -> List[JobPosting]:
    jobs: List[JobPosting] = []
    for r in results.get("results", []):
        url = r.get("url")
        if not url:
            continue
        title = r.get("title", "Job opening")
        content = r.get("content") or ""
        clean_title = re.split(r"[|\-–]", title)[0].strip() or title

        hours_ago = _extract_hours_ago(f"{title} {content}")

        jobs.append(JobPosting(
            id=f"tavily-{hash(url)}",
            title=clean_title,
            company="See listing",
            location=location_label or "Remote",
            source=_guess_source(url),
            url=url,
            posted_at=datetime.now(timezone.utc).isoformat(),
            hours_ago=hours_ago,
            date_verified=hours_ago is not None,
            description=content[:1500],
            tags=[role],
        ))
    return jobs


async def _search_one(client: AsyncTavilyClient, query: str, max_results: int, max_age_hours: int) -> dict:
    # start_date respects the actual configured window (e.g. 6h, 48h, 72h)
    # instead of the fixed "day" bucket, which silently ignored max_age_hours
    # entirely -- moving the "Max age" slider had zero effect on these
    # sources before this fix. Still date-granularity only (Tavily has no
    # sub-day precision), and still based on Tavily's "publish or last
    # updated" ambiguity -- which is exactly why _extract_hours_ago() above
    # is the real freshness authority, not this parameter.
    cutoff_date = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).strftime("%Y-%m-%d")
    async with _SEMAPHORE:
        try:
            return await client.search(
                query=query,
                search_depth="basic",
                topic="general",
                max_results=max_results,
                start_date=cutoff_date,
            )
        except Exception:
            return {}


async def fetch_via_tavily(
    site_key: str,
    roles: List[str],
    max_age_hours: int = 24,
    max_results: int = 15,
) -> List[JobPosting]:
    if not settings.tavily_api_key:
        return []

    domain = SITE_MAP.get(site_key)
    if not domain:
        return []

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    roles = roles or ["software engineer"]
    roles = roles[:4]  # cap queries to control API usage

    queries = [f"{role} remote job site:{domain} posted today" for role in roles]
    results_list = await asyncio.gather(*(_search_one(client, q, max_results, max_age_hours) for q in queries))

    jobs: List[JobPosting] = []
    seen_urls = set()
    for role, results in zip(roles, results_list):
        for job in _jobs_from_results(results, role):
            if job.url in seen_urls:
                continue
            seen_urls.add(job.url)
            jobs.append(job)
    return jobs


async def fetch_country_jobs_via_tavily(
    country_key: str,
    roles: List[str],
    max_age_hours: int = 24,
    max_results: int = 15,
) -> List[JobPosting]:
    """Broad, non-site-restricted discovery for a country, used where no clean
    free/public job-board API exists (unlike Arbeitnow or Adzuna's covered
    countries). Casts a wider net across whatever local boards Tavily indexes."""
    if not settings.tavily_api_key:
        return []

    country_name = COUNTRY_DISPLAY_NAMES.get(country_key)
    if not country_name:
        return []

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    roles = roles or ["software engineer"]
    roles = roles[:4]

    queries = [f"remote {role} jobs {country_name} posted today" for role in roles]
    results_list = await asyncio.gather(*(_search_one(client, q, max_results, max_age_hours) for q in queries))

    jobs: List[JobPosting] = []
    seen_urls = set()
    for role, results in zip(roles, results_list):
        for job in _jobs_from_results(results, role, location_label=f"Remote ({country_name})"):
            if job.url in seen_urls:
                continue
            seen_urls.add(job.url)
            job.tags.append(country_key)
            jobs.append(job)
    return jobs
