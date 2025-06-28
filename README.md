# News Summary Backend

A backend service that fetches news articles via RSS feeds, uses AI to analyze and summarize the top 5 most significant news items per day per region, and serves them through API endpoints.

## Features

- Aggregates news from multiple media sources via RSS feeds
- Scores article importance by region using OpenAI API
- Summarizes top 5 news per day for each region
- Supports multiple timezones and regions
- Persists data using plain JSON files (no database needed)
- FastAPI backend serving summaries via HTTP API

## Requirements

Using either Go or Python, this backend:

- Aggregates news articles from RSS feeds
- Uses AI (e.g., OpenAI API) to identify and summarize the top 5 news items of the day
- Stores data using plain text files (JSON)
- Offers endpoints to:
  - Retrieve today’s top 5 summaries
  - Retrieve summaries from previous days

## Architecture Overview

1. Fetcher collects news from RSS feeds and stores them in `data/raw/{YYYY-MM-DD}/{source}/fetch_{timestamp}.json`
2. Summarizer scores and summarizes articles using OpenAI API, outputting to `data/score_cache/{YYYY-MM-DD}/score_{timestamp}.json`
3. Top-K Precomputer selects the top articles per region and day, storing them in `data/top_k_cache/{region}/{date}.json`
4. FastAPI serves these summaries via `/summary/{region}/{date}` and related endpoints

## Directory Structure

```plaintext
news_summary_backend/
├── app/
│   ├── api/                # FastAPI routes
│   ├── config/             # Region config file
│   └── main.py             # FastAPI entrypoint
├── core/                   # Main logic (fetcher, summarizer, top-k)
├── run/
│   ├── run_all.py          # Run fetcher + summarizer + top-k
│   └── run_topk_precompute.py
├── data/
│   ├── raw/                # Fetched RSS data
│   ├── score_cache/        # Scored articles by date
│   ├── top_k_cache/        # Top K summaries per region/day
│   └── summaries/          # Optional: fallback summary output
```

## API Endpoints

| Endpoint                      | Description                                               |
|------------------------------|-----------------------------------------------------------|
| `/summary/today`             | Returns today's top 5 global summaries                    |
| `/summary/{region}/today`    | Returns today’s top 5 summaries for a specific region     |
| `/summary/{date}`            | Returns global summary for a specific date (YYYY-MM-DD)   |
| `/summary/{region}/{date}`   | Returns region-specific summary for a given date          |

- If no region is specified, summaries are returned for the `global` region by default.
- Dates are interpreted in each region’s timezone, starting from midnight.

## Configuration

Region timezones are configured via `app/config/regions.json`. Example:

```json
{
  "global": "UTC",
  "us": "America/New_York",
  "japan": "Asia/Tokyo",
  "china": "Asia/Shanghai",
  "singapore": "Asia/Singapore"
}

How to Run

Install Dependencies

pip install -r requirements.txt

Run the Pipeline

python run/run_all.py

This runs:
	•	The RSS fetcher
	•	The summarizer (OpenAI-based)
	•	The Top-K precomputer

Run the API Server

uvicorn app.main:app --reload

Test the API

Example requests:

curl http://localhost:8000/summary/today
curl http://localhost:8000/summary/japan/2025-06-27

License

This is a proof-of-concept project. Use and modify freely.

Let me know if you’d like it saved directly into your project as `README.md`.