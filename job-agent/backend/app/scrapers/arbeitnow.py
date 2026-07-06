"""
Arbeitnow (https://arbeitnow.com) runs a genuinely free, public, no-auth JSON
API aimed at Germany/Austria/Switzerland tech jobs plus remote European roles.
No API key required -- this is the most reliable EU-focused source we have,
same tier of reliability as RemoteOK.
"""
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.models.schemas import JobPosting

API_URL = "https://www.arbeitnow.com/api/job-board-api"


async def fetch_arbeitnow_jobs(keywords: Optional[List[str]] = None) -> List[JobPosting]:
    headers = {"User-Agent": "Mozilla/5.0 (JobAgent/1.0; +https://example.com)"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(API_URL, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    entries = payload.get("data", []) if isinstance(payload, dict) else []
    jobs: List[JobPosting] = []
    now = datetime.now(timezone.utc)

    for item in entries:
        if not isinstance(item, dict):
            continue

        created_at = item.get("created_at")
        posted = None
        hours_ago = None
        if created_at:
            try:
                posted = datetime.fromtimestamp(float(created_at), tz=timezone.utc)
                hours_ago = round((now - posted).total_seconds() / 3600, 1)
            except (TypeError, ValueError, OSError):
                posted = None

        title = item.get("title") or ""
        tags = item.get("tags", []) or []
        job_types = item.get("job_types", []) or []
        if keywords:
            haystack = f"{title} {' '.join(tags)} {item.get('description','')}".lower()
            if not any(k.lower() in haystack for k in keywords):
                continue

        jobs.append(JobPosting(
            id=f"arbeitnow-{item.get('slug', hash(item.get('url', title)))}",
            title=title,
            company=item.get("company_name", "Unknown"),
            location=item.get("location") or ("Remote" if item.get("remote") else "Germany/EU"),
            source="Arbeitnow",
            url=item.get("url", "https://www.arbeitnow.com"),
            posted_at=posted.isoformat() if posted else None,
            hours_ago=hours_ago,
            description=(item.get("description") or "")[:2000],
            tags=list(tags) + list(job_types),
        ))
    return jobs
