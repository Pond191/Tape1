from fastapi import FastAPI
from backend.api import routes_health, routes_jobs, routes_transcribe

app = FastAPI(title="DialectTranscribe API")

app.include_router(routes_health.router, prefix="/api", tags=["health"])
app.include_router(routes_transcribe.router, prefix="/api", tags=["transcribe"])
app.include_router(routes_jobs.router, prefix="/api", tags=["jobs"])
