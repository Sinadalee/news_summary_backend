import os
import json
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Dict, Set
from pathlib import Path

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0; +http://example.com/bot)"
}

RSS_SOURCE_FILE = Path("app/config/rss_sources.json")
RAW_DUMP_BASE_DIR = Path("data/raw")
UUID_INDEX_DIR = Path("data/cache/uuid_index")

RAW_DUMP_BASE_DIR.mkdir(parents=True, exist_ok=True)
UUID_INDEX_DIR.mkdir(parents=True, exist_ok=True)

def load_rss_sources() -> Dict[str, str]:
    with open(RSS_SOURCE_FILE, "r") as f:
        return json.load(f)

def get_recent_seen_ids(source_name: str, max_age_days: int) -> Set[str]:
    seen_ids = set()
    cutoff_date = datetime.utcnow().date() - timedelta(days=max_age_days)

    for index_file in sorted((UUID_INDEX_DIR / source_name).glob("*.json")):
        try:
            date_str = index_file.stem
            index_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if index_date < cutoff_date:
                continue
            with open(index_file, "r") as f:
                seen_ids.update(json.load(f))
        except Exception:
            continue
    return seen_ids

def update_seen_ids(source_name: str, fetch_date: str, new_ids: Set[str]):
    source_dir = UUID_INDEX_DIR / source_name
    source_dir.mkdir(parents=True, exist_ok=True)
    index_file = source_dir / f"{fetch_date}.json"

    existing_ids = set()
    if index_file.exists():
        try:
            with open(index_file, "r") as f:
                existing_ids.update(json.load(f))
        except Exception:
            pass

    all_ids = sorted(existing_ids.union(new_ids))
    with open(index_file, "w") as f:
        json.dump(all_ids, f)

def fetch_articles(limit: int = 50, sources: List[str] = None, max_age_days: int = 30) -> List[Dict]:
    rss_sources = load_rss_sources()
    if sources:
        rss_sources = {k: v for k, v in rss_sources.items() if k in sources}

    all_articles = []
    now = datetime.utcnow()
    fetch_date_str = now.strftime("%Y-%m-%d")
    fetch_time_str = now.strftime("%Y-%m-%dT%H-%M-%S")

    for name, url in rss_sources.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        seen_links = get_recent_seen_ids(name, max_age_days)
        new_ids = set()
        articles = []

        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            if not link or link in seen_links:
                continue

            try:
                pub_dt = parsedate_to_datetime(entry.get("published", "")).astimezone(timezone.utc)
            except Exception:
                continue  # Skip if cannot parse date

            pub_str = pub_dt.isoformat()

            article = {
                "title": entry.get("title", ""),
                "link": link,
                "published": pub_str,
                "summary": entry.get("summary", ""),
                "source_name": name,
                "source_url": url
            }

            articles.append(article)
            new_ids.add(link)

        if articles:
            dump_dir = RAW_DUMP_BASE_DIR / fetch_date_str / name
            dump_dir.mkdir(parents=True, exist_ok=True)
            dump_path = dump_dir / f"fetched_{fetch_time_str}.json"
            with open(dump_path, "w") as f:
                json.dump(articles, f, indent=2)

            print(f"Saved {len(articles)} new articles from {name} to {dump_path}")
            all_articles.extend(articles)
            update_seen_ids(name, fetch_date_str, new_ids)
        else:
            print(f"No new articles for {name}")

    return all_articles
