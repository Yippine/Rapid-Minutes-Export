import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from rapid_minutes.config.settings import get_settings
from rapid_minutes.web.routes import router
from rapid_minutes.storage.file_manager import FileManager
from src.rapid_minutes.diagnostics.system_diagnostics import SystemDiagnostics

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Rapid Minutes Export Application")
    file_manager = FileManager()
    await file_manager._initialize_directories()
    yield
    logger.info("Shutting down Rapid Minutes Export Application")

app = FastAPI(
    title="Rapid Minutes Export",
    description="🏆 Excellence-Level AI Meeting Minutes Automation System - Achieving iPhone-level UX, Enterprise-grade stability, and Academic-level code quality",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if isinstance(settings.cors_origins, str) else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapid Minutes Export</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>🎯 Rapid Minutes Export</h1>
            <p>AI-powered meeting minutes generation system</p>
            <p>Please upload static/index.html file to see the full interface</p>
        </body>
        </html>
        """)

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rapid-minutes-export"}

@app.get("/diagnostics")
async def system_diagnostics():
    """Advanced system diagnostics for Phase 3 excellence monitoring"""
    try:
        diagnostics = SystemDiagnostics()
        report = await diagnostics.run_full_diagnostics(enable_auto_repair=False)

        return {
            "timestamp": report.timestamp.isoformat(),
            "overall_score": report.overall_score,
            "overall_status": report.overall_status,
            "summary": report.summary,
            "recommendations": report.recommendations[:10],  # Limit for API response
            "component_scores": {
                component: sum(r.score for r in report.diagnostic_results if r.component == component) /
                          len([r for r in report.diagnostic_results if r.component == component])
                for component in set(r.component for r in report.diagnostic_results)
            }
        }
    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/diagnostics/full")
async def full_system_diagnostics():
    """Complete system diagnostics with auto-repair"""
    try:
        diagnostics = SystemDiagnostics()
        report = await diagnostics.run_full_diagnostics(enable_auto_repair=True)

        # Export detailed report
        await diagnostics.export_diagnostics_report(report, "logs/latest_diagnostics.json")

        return {
            "timestamp": report.timestamp.isoformat(),
            "overall_score": report.overall_score,
            "overall_status": report.overall_status,
            "summary": report.summary,
            "recommendations": report.recommendations,
            "diagnostic_results": [
                {
                    "component": r.component,
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "score": r.score,
                    "message": r.message,
                    "recommendations": r.recommendations
                }
                for r in report.diagnostic_results
            ],
            "repair_results": [
                {
                    "action": r.action.value,
                    "success": r.success,
                    "message": r.message,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in report.repair_results
            ]
        }
    except Exception as e:
        logger.error(f"Full diagnostics error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )