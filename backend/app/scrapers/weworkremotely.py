"""
WeWorkRemotely publishes public RSS feeds per category — no scraping/anti-bot issues.
See https://weworkremotely.com/remote-jobs.rss (and category-specific feeds).

Feeds are fetched concurrently via httpx.AsyncClient rather than with
feedparser.parse(url) directly. feedparser.parse(url) performs a blocking
synchronous network request under the hood, which -- even inside an `async def`
-- freezes the whole event loop for its duration; called in a for-loop across
5 feeds, that serialized ~5x the latency of a single request. Fetching the raw
feed bytes concurrently and handing the already-downloaded text to
feedparser.parse() (a fast, CPU-only parse) avoids that entirely.
"""
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

import feedparser
import httpx

from app.models.schemas import JobPosting

FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]


async def _fetch_feed_text(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


async def fetch_wwr_jobs(keywords: Optional[List[str]] = None) -> List[JobPosting]:
    headers = {"User-Agent": "Mozilla/5.0 (JobAgent/1.0; +https://example.com)"}
    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        feed_texts = await asyncio.gather(*(_fetch_feed_text(client, url) for url in FEEDS))

    jobs: List[JobPosting] = []
    now = datetime.now(timezone.utc)

    for feed_text in feed_texts:
        if not feed_text:
            continue
        parsed = feedparser.parse(feed_text)
        for entry in parsed.entries:
            try:
                posted = parsedate_to_datetime(entry.published)
                if posted.tzinfo is None:
                    posted = posted.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            hours_ago = (now - posted).total_seconds() / 3600

            title = entry.title or ""
            company = "Unknown"
            job_title = title
            if ":" in title:
                company, job_title = title.split(":", 1)

            if keywords:
                haystack = f"{title} {entry.get('summary','')}".lower()
                if not any(k.lower() in haystack for k in keywords):
                    continue

            jobs.append(JobPosting(
                id=f"wwr-{entry.get('id', entry.link)}",
                title=job_title.strip(),
                company=company.strip(),
                location="Remote",
                source="WeWorkRemotely",
                url=entry.link,
                posted_at=posted.isoformat(),
                hours_ago=round(hours_ago, 1),
                description=entry.get("summary", "")[:2000],
                tags=[],
            ))
    return jobs
