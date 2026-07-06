# Job Radar — AI Remote Job Agent

Upload a resume → an LLM (Groq, free tier) extracts your skills/experience →
a LangGraph agent scans multiple remote job boards for postings from the last
24 hours → jobs are ranked by fit → you click "Apply" to go straight to the
real listing.

## Important, honest caveats (read before you build on this)

- **LinkedIn and Indeed prohibit scraping** in their Terms of Service and run
  aggressive anti-bot detection (IP bans, CAPTCHAs, account bans). This project
  does **not** scrape them directly. Instead it uses the **Tavily search API**
  to find publicly indexed postings on those domains and links out to the real
  page. This is legal and robust, but it means Indeed/LinkedIn results are
  "best effort discovery," not a full, guaranteed feed of every new posting.
- **"Apply directly" = one click to the real application page**, not an
  automated bot that fills out LinkedIn's Easy Apply on your behalf while
  logged into your account. Building that would mean automating a real user
  session on a site whose rules forbid it, and it's the kind of thing that
  gets accounts suspended. If you want *fully* automated applying later, look
  at sites that offer an official employer/ATS API (Greenhouse, Lever, Ashby
  all have public APIs) — that's the legitimate way to submit programmatically.
- **RemoteOK** (public JSON API), **WeWorkRemotely** (public RSS feeds), and
  **Arbeitnow** (public JSON API, Germany/Austria/Switzerland + remote EU) are
  used directly since all three explicitly support programmatic access — these
  are your most reliable, real-time sources.
- **Wellfound and Naukri** have no public API, so both are covered via Tavily
  discovery, same as LinkedIn/Indeed.
- **Country-scoped sources** (Germany, Ireland, UK, Poland, Sweden, Denmark,
  Brazil, Chile, Philippines, Malaysia, Indonesia, Japan, Australia, UAE,
  Qatar, Saudi Arabia, Bahrain, Kuwait, Oman): for **UK, Germany, Poland,
  Australia, and Brazil**, this project uses the official **Adzuna API**
  (free tier) directly — real, reliable data, no scraping involved. The
  remaining 14 countries — including all six Middle East / GCC ones, since
  Adzuna doesn't cover that region — have no equivalent free public API we
  could verify, so they fall back to the same Tavily-discovery pattern as
  LinkedIn — best-effort, not a guaranteed full feed. Where both Adzuna and
  Tavily return a source for the same country, results are deduped by URL.
  Dubai and Abu Dhabi are emirates within the UAE, not separate countries, so
  both are covered by the single "UAE" option.
- These are all off by default except Arbeitnow — check the boxes for the
  countries/boards you want, since the Tavily-backed ones consume your Tavily
  free-tier quota per search. "Select all" checkboxes are available for both
  the global-sources group and the regional/country group, and only affect
  their own group.

## Architecture

```
job-agent/
├── backend/                      FastAPI + LangGraph + Groq
│   ├── app/
│   │   ├── main.py               FastAPI app, CORS
│   │   ├── core/config.py        env-based settings
│   │   ├── models/schemas.py     Pydantic models
│   │   ├── services/
│   │   │   ├── resume_parser.py  PDF/DOCX -> text -> Groq LLM -> structured profile
│   │   │   └── job_matcher.py    Groq LLM scores each job 0-100 vs. profile
│   │   ├── scrapers/
│   │   │   ├── remoteok.py       RemoteOK public JSON API
│   │   │   ├── weworkremotely.py WeWorkRemotely public RSS feeds
│   │   │   ├── arbeitnow.py      Arbeitnow public JSON API (Germany/EU)
│   │   │   ├── adzuna.py         Official Adzuna API (UK/Germany/Poland/Australia/Brazil)
│   │   │   └── tavily_search.py  Tavily discovery for LinkedIn/Indeed/Wellfound/Naukri
│   │   │                         + 8 country-scoped fallback searches
│   │   ├── agents/
│   │   │   └── langgraph_agent.py   fetch -> filter by freshness -> score & rank -> filter by criteria
│   │   └── api/routes/
│   │       ├── resume.py         POST /api/resume/upload
│   │       └── jobs.py           POST /api/jobs/search
│   └── requirements.txt
└── frontend/                     React + Vite, "Job Radar" themed UI
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ResumeUpload.jsx
        │   ├── ProfileSummary.jsx
        │   ├── FilterPanel.jsx
        │   ├── JobList.jsx
        │   └── JobCard.jsx
        └── styles/index.css
```

## Setup

### 1. Get free API keys
- Groq: https://console.groq.com/keys (free tier, fast Llama models)
- Tavily: https://app.tavily.com (free tier, ~1000 searches/month)
- Adzuna (optional): https://developer.adzuna.com/signup (free tier, official
  API for UK/Germany/Poland/Australia/Brazil — skip this and those countries
  just fall back to Tavily discovery)
- Langfuse (optional, for monitoring — see below): https://cloud.langfuse.com (free tier)

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env with your API keys
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173

## API

**POST `/api/resume/upload`** — multipart file upload (`file` field, pdf/docx/txt)
→ returns a structured `ResumeProfile` (name, skills, years experience, preferred roles, summary).

**POST `/api/jobs/search`**
```json
{
  "profile": { ...ResumeProfile... },
  "sources": ["remoteok", "weworkremotely", "linkedin", "indeed", "wellfound", "naukri", "arbeitnow", "germany", "uk", "poland", "australia", "brazil", "ireland", "sweden", "denmark", "chile", "philippines", "malaysia", "indonesia", "japan", "uae", "qatar", "saudi_arabia", "bahrain", "kuwait", "oman"],
  "max_age_hours": 24,
  "min_match_score": 70,
  "min_experience_years": 2,
  "max_experience_years": 6
}
```
`sources` is one flat list mixing global boards (`remoteok`, `weworkremotely`,
`linkedin`, `indeed`, `wellfound`, `naukri`, `arbeitnow`) with country keys
(the 19 listed above) — a country key pulls from Adzuna where officially
supported (`germany`, `uk`, `poland`, `australia`, `brazil`) combined with
Tavily discovery, or Tavily discovery alone for the rest — including all six
Middle East/GCC keys (`uae`, `qatar`, `saudi_arabia`, `bahrain`, `kuwait`,
`oman`; note `uae` covers Dubai and Abu Dhabi, which are emirates within it,
not separate countries).
→ returns jobs ranked by `match_score`, plus `total_found` / `total_after_filter` counts.

`min_match_score` (0-100, default 0) drops anything below that fit score — the
scoring prompt is instructed to score off-domain jobs (e.g. sales/marketing for
a software candidate) below 30 regardless of surface keyword overlap, so a
threshold of 70 reliably cuts out other-domain noise.

`min_experience_years` / `max_experience_years` filter by the experience band
each job is estimated to want, which the LLM infers from the posting's
title/description (`required_experience_min` / `required_experience_max` on
each returned job). A posting is kept if its band overlaps your requested
range at all, or if the band couldn't be determined — postings are never
dropped on missing info, only on being genuinely out of range.

**POST `/api/jobs/export`**
```json
{ "jobs": [ ...JobPosting... ] }
```
→ returns a formatted `.xlsx` file (`Content-Disposition: attachment`) built
with openpyxl: bold header row, frozen header, real Excel Table (built-in
sort/filter dropdowns), and a clickable hyperlink per row linking straight to
the posting. Send it whatever job list is currently shown in the UI — the
"Export to Excel" button next to the results does exactly this with the
current search results. 400s if `jobs` is empty.

## Monitoring (Langfuse)

Every LLM call and every LangGraph node is instrumented for tracing, latency,
token usage, and cost via [Langfuse](https://langfuse.com) (open source, free
tier on their cloud, or self-host for free with Docker).

**It's fully optional and off by default.** Leave `LANGFUSE_PUBLIC_KEY` /
`LANGFUSE_SECRET_KEY` blank in `.env` and the app runs exactly as before —
no code path changes, no crashes, no dangling network calls.

To turn it on:
1. Sign up free at https://cloud.langfuse.com (or self-host —
   https://langfuse.com/self-hosting) and create a project.
2. Copy the Public Key / Secret Key from Project Settings → API Keys into `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
3. Restart the backend. Check `GET /api/health` — `langfuse_monitoring` will
   read `true`.
4. Upload a resume and run a job search, then open your Langfuse project
   dashboard. You'll see:
   - A **`job-search-agent`** trace per search, with a span for each LangGraph
     node (`fetch_sources` → `filter_by_freshness` → `score_and_rank`),
     including how long each one took.
   - A **`resume-extraction`** trace for the resume-parsing LLM call, and one
     **`job-scoring-batch-N`** trace per batch of jobs scored — each showing
     the exact prompt, response, token counts, and cost (Groq's per-token
     pricing, or $0 if you're on a free Groq tier that doesn't bill).

All of this lives in `backend/app/core/observability.py` — a single module
that every LLM call site and the LangGraph entry point import from, so adding
monitoring to a new node or a new LLM call anywhere else in the app is just:
```python
from app.core.observability import get_langfuse_handler

config = {"run_name": "my-new-step"}
if handler := get_langfuse_handler():
    config["callbacks"] = [handler]

result = llm.invoke(messages, config=config)
```

## Performance

Three real concurrency bugs were fixed (not just "external APIs are slow" —
these caused genuine, avoidable serialization):

- **Tavily discovery** (`tavily_search.py`) previously used the *synchronous*
  `TavilyClient` and called `.search()` directly inside an `async def`. That
  blocks Python's single-threaded event loop for the full call duration, so
  even though sources were wrapped in `asyncio.gather()`, they secretly ran
  one at a time. Switched to `AsyncTavilyClient` with real `await`, and the
  per-role queries (up to 4 per source) now run concurrently too, bounded by
  a semaphore (max 6 at once) to stay a good API citizen.
- **WeWorkRemotely** (`weworkremotely.py`) called `feedparser.parse(url)` —
  itself a blocking network call — in a sequential loop across 5 RSS feeds.
  Now fetches all 5 feed bodies concurrently via `httpx.AsyncClient`, then
  parses the already-downloaded text (fast, CPU-only, no blocking).
- **Job scoring** (`job_matcher.py`) called the Groq LLM's synchronous
  `.invoke()` once per batch of 15 jobs, in a sequential loop. Switched to
  `.ainvoke()` with `asyncio.gather()` across batches (bounded by a
  semaphore of 4 concurrent Groq calls), and also moved resume parsing's
  blocking LLM call into a background thread (`asyncio.to_thread`) so it no
  longer freezes the server for other concurrent requests while it runs.

Measured with simulated per-call latency standing in for real network time
(since sandboxed testing can't hit live Tavily/Groq): 16 simulated Tavily
calls went from ~4.8s sequential to ~0.9s concurrent; 5 WWR feeds went from
~1.5s to ~0.3s; scoring 60 jobs across 4 batches went from ~2.0s to ~0.5s.
Real-world savings will vary with actual API latency and how many
sources/countries you have checked, but the shape of the improvement holds:
work that should overlap now actually overlaps.

If searches still feel slow after this, the biggest remaining lever is how
many sources/countries you have checked at once — each Tavily-backed one
adds more queries to the pool the semaphore has to work through. Trim to the
sources you actually care about, or raise `max_age_hours` less aggressively,
for a faster search.

## Freshness accuracy

Search-discovered sources (LinkedIn, Indeed, Wellfound, Naukri, and the 14
Tavily-backed country boards) can return jobs older than your requested
window even when everything else works correctly, because of a real
limitation in Tavily's API: its `results[]` objects have **no published-date
field at all**, and its `time_range` filter is documented as filtering by
"publish date **or last updated date**" — meaning a job listing page that got
re-crawled or re-cached recently can pass a "last 24 hours" filter even
though the specific job posting on it is a month old.

To fix this rather than just trust the filter, every Tavily-discovered result
is scanned for a real relative-age phrase in its title/snippet ("posted 3
days ago", "2 hours ago", "yesterday", "30+ days ago", etc.) and that's used
as the actual `hours_ago` when found. Each `JobPosting` also carries a
`date_verified` boolean: `true` when the age comes from a real timestamp
(RemoteOK/WWR/Arbeitnow/Adzuna) or a parsed relative-age phrase, `false` when
no age signal could be found at all.

By default (`require_verified_freshness: true`), unverified-date jobs are
**dropped** rather than assumed fresh — this is what actually fixes "I asked
for 24 hours and got a job from a month ago." There's a toggle in the UI
("Only show verified-fresh dates") to turn this off if you'd rather see more
results with unconfirmed timing; even with it off, any job whose age was
positively identified as too old is still excluded — turning it off only
affects jobs where the age genuinely couldn't be determined either way.

Separately, the Tavily query itself previously always requested a fixed
"last 24 hours" window (`time_range="day"`) no matter what your "Max age"
slider was set to — moving it to 6h or 72h had zero effect on these sources.
It now computes an actual `start_date` from your chosen `max_age_hours`, so
the slider genuinely changes what Tavily is asked for (still date-granularity
only, and still subject to the "last updated" ambiguity above — which is why
the relative-age text scan is the real authority, not this parameter).

## Extending this

- Swap the Groq model in `.env` (`GROQ_MODEL`) for any Groq-hosted model.
- Add a new board by writing a new file in `backend/app/scrapers/` that returns
  a list of `JobPosting`, then wire it into `langgraph_agent.py`'s
  `fetch_sources_node`.
- Add a LangGraph node for auto-generating a tailored cover letter per job
  using the same Groq LLM — the graph is built to make this a one-node addition.
