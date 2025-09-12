"""
FastAPI Application Entry Point (C01)
Main application based on SYSTEM_ARCHITECTURE.md specifications
Implements SESE principles: Simple, Effective, Systematic, Exhaustive
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Import application components
from .config import settings
from .api import upload, process, download
from .utils.logger import setup_logging
from .utils.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting Rapid Minutes Export Application")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    
    # Ensure required directories exist
    ensure_directories()
    
    # Initialize AI services
    await initialize_services()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Rapid Minutes Export Application")
    await cleanup_services()


def create_application() -> FastAPI:
    """
    Create FastAPI application with all middleware and routes
    Implements ICE principle: Intuitive, Concise, Encompassing
    """
    
    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Meeting Minutes Generation System - Transform messy transcripts into professional Word documents",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    add_custom_middleware(app)
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Include API routes
    include_api_routes(app)
    
    # Mount static files
    mount_static_files(app)
    
    # Add main routes
    add_main_routes(app)
    
    return app


def add_custom_middleware(app: FastAPI):
    """Add custom middleware for logging and performance"""
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests"""
        start_time = time.time()
        
        # Log request
        logger.info(f"🌐 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'Unknown'}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"✅ {response.status_code} - {process_time:.3f}s")
        
        return response


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


def include_api_routes(app: FastAPI):
    """Include all API routes with prefix"""
    app.include_router(
        upload.router,
        prefix=settings.api_prefix,
        tags=["Upload"]
    )
    app.include_router(
        process.router,
        prefix=settings.api_prefix,
        tags=["Processing"]
    )
    app.include_router(
        download.router,
        prefix=settings.api_prefix,
        tags=["Download"]
    )


def mount_static_files(app: FastAPI):
    """Mount static file directories"""
    # Mount static files
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_dir)),
        name="static"
    )


def add_main_routes(app: FastAPI):
    """Add main application routes"""
    
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def read_root():
        """Serve main application page"""
        try:
            index_path = settings.static_dir / "index.html"
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            else:
                return HTMLResponse(
                    content="""
                    <html>
                        <head><title>Rapid Minutes Export</title></head>
                        <body>
                            <h1>🎯 Rapid Minutes Export</h1>
                            <p>AI Meeting Minutes Automation System</p>
                            <p>Main interface file not found. Please ensure static/index.html exists.</p>
                        </body>
                    </html>
                    """,
                    status_code=200
                )
        except Exception as e:
            logger.error(f"Error serving root page: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/health", include_in_schema=False)
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/metrics", include_in_schema=False)
    async def get_metrics():
        """Basic metrics endpoint"""
        if not settings.enable_metrics:
            raise HTTPException(status_code=404, detail="Metrics not enabled")
        
        return {
            "app_info": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment
            },
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        settings.data_dir,
        settings.input_dir,
        settings.output_dir,
        settings.temp_dir,
        settings.templates_dir,
        settings.word_template_dir,
        settings.log_file.parent
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"📁 Ensured directory exists: {directory}")


async def initialize_services():
    """Initialize external services and connections"""
    try:
        # Test Ollama connection
        from .ai.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        is_connected = await ollama_client.health_check()
        
        if is_connected:
            logger.info("🤖 Ollama service connection verified")
        else:
            logger.warning("⚠️ Ollama service not available - AI processing may fail")
        
        # Verify template files exist
        template_path = settings.template_path
        if template_path.exists():
            logger.info(f"📄 Default template found: {template_path}")
        else:
            logger.warning(f"⚠️ Default template not found: {template_path}")
        
        logger.info("✅ Service initialization completed")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        # Don't fail startup for service issues in development
        if not settings.is_development:
            raise


async def cleanup_services():
    """Cleanup services and connections on shutdown"""
    try:
        # Cleanup temporary files
        temp_files = list(settings.temp_dir.glob("*"))
        for temp_file in temp_files:
            if temp_file.is_file() and temp_file.stat().st_mtime < (time.time() - 3600):
                temp_file.unlink()
        
        logger.info("🧹 Temporary files cleaned up")
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


# Import required modules for middleware
import time
from datetime import datetime


# Create application instance
app = create_application()


def run_development():
    """Run application in development mode"""
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.reload,
        reload_dirs=settings.get_reload_dirs_list() if settings.reload else None,
        log_level=settings.log_level.lower(),
        access_log=True
    )


def run_production():
    """Run application in production mode"""
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    """Direct execution entry point"""
    logger.info(f"🎯 Starting {settings.app_name} v{settings.app_version}")
    
    if settings.is_development:
        logger.info("🔧 Running in development mode")
        run_development()
    else:
        logger.info("🏭 Running in production mode")
        run_production()