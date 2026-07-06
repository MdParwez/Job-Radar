# Job Radar – AI-Powered  Job Search Agent

## Overview

Job Radar is an AI-powered job discovery platform that helps candidates find highly relevant  job opportunities based on their resume. Instead of relying on keyword matching, the system uses Large Language Models (LLMs) and an agentic workflow to understand a candidate's profile, search multiple job sources, rank opportunities by relevance, and present the best matches.

The project is designed to automate the most time-consuming part of a job search while keeping the final application process under the user's control.

---

## Problem Statement

Searching for relevant jobs across multiple platforms is repetitive and inefficient. Traditional job portals rely heavily on keyword matching, often returning many irrelevant results.

Job Radar addresses this by understanding a candidate's skills, experience, preferred roles, and technologies, then intelligently ranking job opportunities based on semantic similarity rather than simple keyword overlap.

---

## How It Works

1. The user uploads a resume (PDF, DOCX, or TXT).
2. A Groq-powered LLM extracts structured information such as:

   * Skills
   * Experience
   * Preferred roles
   * Professional summary
3. A LangGraph agent coordinates job collection from multiple supported job sources.
4. Jobs are filtered based on freshness and user-defined criteria.
5. The LLM evaluates each job against the candidate's profile and assigns a match score.
6. Results are ranked and presented with direct links to the original job postings.

---

## Architecture

```
Resume Upload
        │
        ▼
Resume Parser (Groq LLM)
        │
        ▼
Structured Candidate Profile
        │
        ▼
LangGraph Agent
        │
 ┌──────┼───────────────┐
 │      │               │
 ▼      ▼               ▼
Job Sources         Search APIs
(RemoteOK, WWR,    (Tavily,
Arbeitnow,         Adzuna)
etc.)
        │
        ▼
Job Aggregation
        │
        ▼
Freshness Filtering
        │
        ▼
LLM-Based Job Scoring
        │
        ▼
Ranking & Recommendations
        │
        ▼
React Dashboard
```

---

## Key Features

* AI-powered resume understanding using Groq LLM
* Agentic workflow built with LangGraph
* Multi-source job aggregation
* Semantic job matching instead of keyword matching
* Intelligent ranking based on profile relevance
* Freshness-based filtering for recently posted jobs
* Direct redirection to original job listings
* Excel export for shortlisted opportunities

---

## Technology Stack

### Backend

* FastAPI
* Python
* LangGraph
* Groq LLM
* Pydantic
* AsyncIO
* HTTPX

### Frontend

* React
* Vite

### AI & Agentic Components

* Groq LLM
* LangGraph
* Prompt Engineering
* LLM-based Resume Parsing
* AI-powered Job Ranking

### Data Sources

* RemoteOK
* WeWorkRemotely
* Arbeitnow
* Adzuna
* Tavily Search

---

## Highlights

* Uses an LLM to understand resumes instead of relying on keyword extraction.
* Employs an agentic workflow to coordinate data collection, filtering, and ranking.
* Aggregates jobs from multiple public sources into a single search experience.
* Uses semantic scoring to recommend the most relevant opportunities based on candidate profiles.
* Built with asynchronous processing to efficiently handle multiple job sources concurrently.

