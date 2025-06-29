# scripts/run_fetcher.py

import json
import click
from app.core.fetcher import fetch_articles

@click.command()
@click.option('--limit', default=50, help="Max articles to fetch per source")
def main(limit):
    articles = fetch_articles(limit=limit)
    print(f"Total new articles fetched: {len(articles)}")

if __name__ == "__main__":
    main()