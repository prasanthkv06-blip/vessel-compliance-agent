from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import vessel, report
from .config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Vessel Compliance Automation Agent for S&P Inspections",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vessel.router)
app.include_router(report.router)

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
