from app.core.fetcher.fetcher import fetch_articles

if __name__ == "__main__":
    fetch_articles(region="us", limit=50)