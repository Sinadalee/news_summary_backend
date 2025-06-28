import os
import json
from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter()
SUMMARY_DIR = "data/summaries"

def load_summary(date_str: str):
    path = os.path.join(SUMMARY_DIR, f"summarized_{date_str}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Summary not found for this date.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

@router.get("/summary/today")
def get_today_summary():
    today = datetime.now().date().isoformat()
    return {"date": today, "articles": load_summary(today)}

@router.get("/summary/{date}")
def get_summary_by_date(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    return {"date": date, "articles": load_summary(date)}