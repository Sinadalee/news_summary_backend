News Summary Backend

This project is a lightweight backend for collecting, summarizing, and serving top news stories regionally and globally.

Features
	•	Aggregates news articles from multiple RSS feeds.
	•	Uses GPT (via OpenAI API) to summarize and score articles by importance and frequency.
	•	Stores data using plain JSON files, no database required.
	•	Supports real-time summarization with socket-based communication.
	•	Provides API endpoints to access top summaries by region and date.

Requirements

Using either Go or Python, this backend:
	•	Aggregates news articles from RSS feeds
	•	Uses AI (e.g., OpenAI API) to identify and summarize the top 5 news items of the day
	•	Stores data using plain text files (JSON)
	•	Offers endpoints to:
	•	Retrieve today’s top 5 summaries
	•	Retrieve summaries from previous days

Project Structure

.
├── app/
│   ├── api/                # FastAPI routes
│   ├── core/               # Summarizer and sender logic
│   ├── config/             # Region and port configuration
├── data/                   # Raw articles, summaries, logs, caches
├── .venv/                  # Virtual environment
├── main.py                 # FastAPI entry point
├── sender_us.py            # Example sender script (runs with cron)
├── receiver.py             # Socket listener for processing fetched files

Setup

1. Install dependencies

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

2. Environment

Create a .env file with your OpenAI key:

OPENAI_API_KEY=your-api-key

3. Start the API server

uvicorn app.main:app --reload

4. Start the receiver

python app/core/receiver.py

By default, each region receiver listens on its own port (see app/config/ports.json).

5. Trigger the sender (example for US)

You can schedule it via cron:

* * * * * /path/to/project/.venv/bin/python /path/to/project/sender_us.py >> /tmp/sender_us.log 2>&1

Or run manually for testing:

python sender_us.py

API Endpoints
	•	GET /summary/today?region=us
Returns today’s top 5 summaries for the specified region (defaults to us).
	•	GET /summary/{date}?region=jp
Returns top 5 summaries for a given date and region (date format: YYYY-MM-DD).

Configuration
	•	app/config/regions.json: Maps region codes to timezones.
	•	app/config/ports.json: Maps region codes to receiver socket ports.

Notes
	•	Each fetched_*.json file is processed once and then moved to a backup directory.
	•	Summary results are cached by UUID and deduplicated using article title + link.
	•	Top 5 summaries are precomputed and stored under data/top_k_cache/{region}/{YYYY-MM-DD}.json.
