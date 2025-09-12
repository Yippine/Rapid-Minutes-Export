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
    file_manager.ensure_directories()
    yield
    logger.info("Shutting down Rapid Minutes Export Application")

app = FastAPI(
    title="Rapid Minutes Export",
    description="AI-powered meeting minutes generation from text to Word documents",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rapid-minutes-export"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )