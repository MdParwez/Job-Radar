"""
RemoteOK has a public, scrape-friendly JSON API: https://remoteok.com/api
No auth required and it's explicitly meant for programmatic use.
"""
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.models.schemas import JobPosting


async def fetch_remoteok_jobs(keywords: Optional[List[str]] = None) -> List[JobPosting]:
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "Mozilla/5.0 (JobAgent/1.0; +https://example.com)"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    jobs: List[JobPosting] = []
    now = datetime.now(timezone.utc)
    for item in data:
        if not isinstance(item, dict) or "id" not in item or "date" not in item:
            continue
        try:
            posted = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
        except Exception:
            continue
        hours_ago = (now - posted).total_seconds() / 3600

        title = item.get("position") or item.get("title") or ""
        tags = item.get("tags", []) or []
        if keywords:
            haystack = f"{title} {' '.join(tags)} {item.get('description','')}".lower()
            if not any(k.lower() in haystack for k in keywords):
                continue

        jobs.append(JobPosting(
            id=f"remoteok-{item.get('id')}",
            title=title,
            company=item.get("company", "Unknown"),
            location=item.get("location") or "Remote",
            source="RemoteOK",
            url=item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
            posted_at=posted.isoformat(),
            hours_ago=round(hours_ago, 1),
            description=(item.get("description") or "")[:2000],
            tags=tags,
            salary=item.get("salary") or None,
        ))
    return jobs
