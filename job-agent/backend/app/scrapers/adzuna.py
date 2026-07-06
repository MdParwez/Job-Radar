"""
Adzuna (https://developer.adzuna.com) runs an official REST API with a free
tier (app_id + app_key, no cost for reasonable volume). Its officially
supported countries include several from this project's requested list:
UK, Germany, Poland, Australia, and Brazil -- so we use it directly for those,
rather than relying only on Tavily discovery.

Fully optional: with no ADZUNA_APP_ID/APP_KEY configured, this scraper just
returns an empty list (same graceful-degradation pattern as Tavily/Groq).

Note: Adzuna's terms require attribution ("Jobs by Adzuna" + logo) if you
publicly display their listings at any real scale -- see
https://developer.adzuna.com/docs/terms_of_service. Fine for personal/local
use; add the attribution badge if you deploy this for other people.
"""
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.core.config import settings
from app.models.schemas import JobPosting

# Only the countries Adzuna's API officially supports, among the ones this
# project cares about. Everything else in the requested country list falls
# back to Tavily's country-scoped discovery instead.
ADZUNA_COUNTRY_CODES = {
    "uk": "gb",
    "germany": "de",
    "poland": "pl",
    "australia": "au",
    "brazil": "br",
}


async def fetch_adzuna_jobs(
    country_key: str,
    roles: Optional[List[str]] = None,
    max_results: int = 20,
) -> List[JobPosting]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    country_code = ADZUNA_COUNTRY_CODES.get(country_key)
    if not country_code:
        return []

    roles = roles or ["software engineer"]
    query = roles[0]  # Adzuna's `what` param takes one phrase at a time

    url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "what": query,
        "results_per_page": max_results,
        "max_days_old": 1,  # Adzuna's own recency filter, matches our freshness goal
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return []

    entries = payload.get("results", []) if isinstance(payload, dict) else []
    jobs: List[JobPosting] = []
    now = datetime.now(timezone.utc)

    for item in entries:
        if not isinstance(item, dict):
            continue

        created = item.get("created")
        posted = None
        hours_ago = None
        if created:
            try:
                posted = datetime.fromisoformat(created.replace("Z", "+00:00"))
                hours_ago = round((now - posted).total_seconds() / 3600, 1)
            except (TypeError, ValueError):
                posted = None

        location_obj = item.get("location") or {}
        location = location_obj.get("display_name") if isinstance(location_obj, dict) else None

        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary = None
        if salary_min and salary_max:
            salary = f"{int(salary_min):,}-{int(salary_max):,}"

        jobs.append(JobPosting(
            id=f"adzuna-{item.get('id', item.get('redirect_url', ''))}",
            title=item.get("title", "Job opening"),
            company=(item.get("company") or {}).get("display_name", "Unknown"),
            location=location or country_key,
            source="Adzuna",
            url=item.get("redirect_url", "https://www.adzuna.com"),
            posted_at=posted.isoformat() if posted else None,
            hours_ago=hours_ago,
            description=(item.get("description") or "")[:2000],
            tags=[],
            salary=salary,
        ))
    return jobs
