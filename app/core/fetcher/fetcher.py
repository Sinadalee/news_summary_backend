import os
import json
import socket
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Dict
from pathlib import Path

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0; +http://example.com/bot)"
}

PORT_CONFIG_PATH = Path("app/config/ports.json")
RSS_SOURCE_FILE = Path("app/config/rss_sources.json")
REGION_SOURCE_FILE = Path("app/config/region_sources.json")
STATUS_DB_FILE = Path("data/cache/article_status.json")
RAW_DUMP_BASE_DIR = Path("data/raw")

RAW_DUMP_BASE_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
if not STATUS_DB_FILE.exists():
    with open(STATUS_DB_FILE, "w") as f:
        json.dump({}, f)

def load_rss_sources() -> Dict[str, str]:
    with open(RSS_SOURCE_FILE, "r") as f:
        return json.load(f)

def load_region_sources() -> Dict[str, List[str]]:
    with open(REGION_SOURCE_FILE, "r") as f:
        return json.load(f)

def load_article_status() -> Dict[str, Dict]:
    try:
        with open(STATUS_DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_article_status(status_data: Dict[str, Dict]):
    with open(STATUS_DB_FILE, "w") as f:
        json.dump(status_data, f, indent=2)

def notify_via_socket(message: Dict, host="localhost"):
    try:
        with open(PORT_CONFIG_PATH, "r") as f:
            port_config = json.load(f)

        region = message.get("region")
        if not region or region not in port_config:
            raise ValueError(f"Region '{region}' not found in port config.")

        port = port_config[region]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(json.dumps(message).encode())
    except Exception as e:
        print(f"[SOCKET ERROR] Could not send message to queue: {e}")

def fetch_articles(region: str = None, limit: int = 50, sources: List[str] = None) -> List[Dict]:
    rss_sources = load_rss_sources()
    region_sources = load_region_sources()
    status_db = load_article_status()

    region_lookup = {}
    for reg, source_list in region_sources.items():
        for src in source_list:
            region_lookup[src] = reg

    if sources:
        rss_sources = {k: v for k, v in rss_sources.items() if k in sources}
    elif region:
        source_list = region_sources.get(region, [])
        rss_sources = {k: v for k, v in rss_sources.items() if k in source_list}

    all_articles = []
    now = datetime.utcnow()
    fetch_date_str = now.strftime("%Y-%m-%d")
    fetch_time_str = now.strftime("%Y-%m-%dT%H-%M-%S")

    for name, url in rss_sources.items():
        region = region_lookup.get(name, "unknown")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            continue

        new_articles = []

        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            if not link or (link in status_db and status_db[link]["status"] == "done"):
                continue

            try:
                pub_dt = parsedate_to_datetime(entry.get("published", "")).astimezone(timezone.utc)
            except Exception:
                continue

            pub_str = pub_dt.isoformat()
            article = {
                "title": entry.get("title", ""),
                "link": link,
                "published": pub_str,
                "summary": entry.get("summary", ""),
                "source_name": name,
                "source_url": url,
                "region": region
            }

            new_articles.append(article)
            status_db[link] = {"uuid": None, "status": "fetched"}

        if new_articles:
            dump_dir = RAW_DUMP_BASE_DIR / region / fetch_date_str / name
            dump_dir.mkdir(parents=True, exist_ok=True)
            dump_path = dump_dir / f"fetched_{fetch_time_str}.json"

            with open(dump_path, "w") as f:
                json.dump(new_articles, f, indent=2)

            print(f"[OK] Saved {len(new_articles)} new articles from {name} to {dump_path}")
            notify_via_socket({
                "task": "summarize",
                "region": region,
                "source": name,
                "file": str(dump_path)
            })

            all_articles.extend(new_articles)

    save_article_status(status_db)
    return all_articles