from fastapi import FastAPI
from app.api.routes import router as summary_routes

app = FastAPI(title="News Summary API")

app.include_router(summary_routes)