import os
import json
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from zoneinfo import ZoneInfo

router = APIRouter()

SUMMARY_DIR = "data/top_k_cache"
REGION_CONFIG = "app/config/regions.json"

# Load region → timezone mapping
with open(REGION_CONFIG, "r") as f:
    REGION_TIMEZONES = json.load(f)


def resolve_region(region: str | None) -> str:
    """Ensure region is valid, fallback to 'us' only if region is None."""
    if region is None:
        return "us"
    if region not in REGION_TIMEZONES:
        raise HTTPException(status_code=404, detail=f"Region '{region}' is not supported.")
    return region


def get_local_date(region: str) -> str:
    tz = ZoneInfo(REGION_TIMEZONES[region])
    return datetime.now(tz).date().isoformat()


def load_summary(date_str: str, region: str):
    path = os.path.join(SUMMARY_DIR, region, f"{date_str}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Summary not found for {region} on {date_str}.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/summary/today")
def get_today_summary(region: str = Query(default="us", description="Region code like 'us', 'jp', etc.")):
    region = resolve_region(region)
    today = get_local_date(region)
    return {
        "region": region,
        "date": today,
        "articles": load_summary(today, region)
    }


@router.get("/summary/{date}")
def get_summary_by_date(
    date: str,
    region: str = Query(default="us", description="Region code like 'us', 'jp', etc.")
):
    region = resolve_region(region)
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    return {
        "region": region,
        "date": date,
        "articles": load_summary(date, region)
    }