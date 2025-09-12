"""
Configuration Management System (C02)
Centralized configuration based on SYSTEM_ARCHITECTURE.md specifications
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
import os

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, validator
except ImportError:
    from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file"""
    
    # Application Configuration
    app_name: str = Field(default="Rapid-Minutes-Export", env="APP_NAME")
    app_version: str = Field(default="0.5.0", env="APP_VERSION")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=True, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Ollama AI Configuration
    ollama_host: str = Field(default="localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3.1:8b", env="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=60, env="OLLAMA_TIMEOUT")
    ollama_max_retries: int = Field(default=3, env="OLLAMA_MAX_RETRIES")
    
    # File Paths Configuration
    templates_dir: Path = Field(default=Path("./templates"), env="TEMPLATES_DIR")
    data_dir: Path = Field(default=Path("./data"), env="DATA_DIR")
    input_dir: Path = Field(default=Path("./data/input"), env="INPUT_DIR")
    output_dir: Path = Field(default=Path("./data/output"), env="OUTPUT_DIR")
    temp_dir: Path = Field(default=Path("./data/temp"), env="TEMP_DIR")
    static_dir: Path = Field(default=Path("./static"), env="STATIC_DIR")
    
    # File Processing Configuration
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(default=".txt", env="ALLOWED_FILE_TYPES")
    upload_timeout_seconds: int = Field(default=30, env="UPLOAD_TIMEOUT_SECONDS")
    processing_timeout_seconds: int = Field(default=300, env="PROCESSING_TIMEOUT_SECONDS")
    cleanup_interval: int = Field(default=3600, env="CLEANUP_INTERVAL")
    
    # Document Generation Configuration
    default_template: str = Field(default="default_meeting.docx", env="DEFAULT_TEMPLATE")
    word_template_dir: Path = Field(default=Path("./templates/word"), env="WORD_TEMPLATE_DIR")
    pdf_output_quality: str = Field(default="high", env="PDF_OUTPUT_QUALITY")
    document_author: str = Field(default="Rapid-Minutes-Export", env="DOCUMENT_AUTHOR")
    
    # API Configuration
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000",
        env="CORS_ORIGINS"
    )
    max_request_size_mb: int = Field(default=15, env="MAX_REQUEST_SIZE_MB")
    
    # Security Configuration
    secret_key: str = Field(
        default="rapid-minutes-export-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,0.0.0.0",
        env="ALLOWED_HOSTS"
    )
    trust_host_header: bool = Field(default=False, env="TRUST_HOST_HEADER")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Path = Field(default=Path("./logs/app.log"), env="LOG_FILE")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_max_size_mb: int = Field(default=10, env="LOG_MAX_SIZE_MB")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Performance Configuration
    workers: int = Field(default=1, env="WORKERS")
    worker_connections: int = Field(default=1000, env="WORKER_CONNECTIONS")
    max_concurrent_processes: int = Field(default=5, env="MAX_CONCURRENT_PROCESSES")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    
    # Development Configuration
    reload: bool = Field(default=True, env="RELOAD")
    reload_dirs: str = Field(default="app,static,templates", env="RELOAD_DIRS")
    hot_reload: bool = Field(default=True, env="HOT_RELOAD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("templates_dir", "data_dir", "input_dir", "output_dir", "temp_dir", "static_dir", "word_template_dir")
    def ensure_path_exists(cls, v):
        """Ensure directory paths exist"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @validator("log_file")
    def ensure_log_dir_exists(cls, v):
        """Ensure log directory exists"""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path
    
    @validator("cors_origins")
    def validate_cors_origins(cls, v):
        """Parse CORS origins string into list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("allowed_hosts")
    def validate_allowed_hosts(cls, v):
        """Parse allowed hosts string into list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    @validator("allowed_file_types")
    def validate_file_types(cls, v):
        """Parse file types string into list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v
    
    @validator("reload_dirs")
    def validate_reload_dirs(cls, v):
        """Parse reload directories string into list"""
        if isinstance(v, str):
            return [dir.strip() for dir in v.split(",") if dir.strip()]
        return v
    
    @validator("max_file_size_mb")
    def validate_max_file_size(cls, v):
        """Ensure max file size is reasonable"""
        if v <= 0 or v > 100:
            raise ValueError("Max file size must be between 1 and 100 MB")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Ensure log level is valid"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("pdf_output_quality")
    def validate_pdf_quality(cls, v):
        """Ensure PDF quality setting is valid"""
        valid_qualities = ["low", "medium", "high"]
        if v.lower() not in valid_qualities:
            raise ValueError(f"PDF quality must be one of: {valid_qualities}")
        return v.lower()
    
    # Computed properties
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def max_request_size_bytes(self) -> int:
        """Convert max request size to bytes"""
        return self.max_request_size_mb * 1024 * 1024
    
    @property
    def log_max_size_bytes(self) -> int:
        """Convert log max size to bytes"""
        return self.log_max_size_mb * 1024 * 1024
    
    @property
    def ollama_url(self) -> str:
        """Get full Ollama URL"""
        if not self.ollama_host.startswith(('http://', 'https://')):
            return f"http://{self.ollama_host}"
        return self.ollama_host
    
    @property
    def template_path(self) -> Path:
        """Get full path to default template"""
        return self.word_template_dir / self.default_template
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() in ["production", "prod"]
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins
    
    def get_allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as list"""
        if isinstance(self.allowed_hosts, str):
            return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return self.allowed_hosts
    
    def get_allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as list"""
        if isinstance(self.allowed_file_types, str):
            return [ext.strip() for ext in self.allowed_file_types.split(",") if ext.strip()]
        return self.allowed_file_types
    
    def get_reload_dirs_list(self) -> List[str]:
        """Get reload directories as list"""
        if isinstance(self.reload_dirs, str):
            return [dir.strip() for dir in self.reload_dirs.split(",") if dir.strip()]
        return self.reload_dirs


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching
    Uses lru_cache to ensure settings are loaded only once
    """
    return Settings()


# Global settings instance
settings = get_settings()


class DatabaseSettings(BaseSettings):
    """Database configuration (future use)"""
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class RedisSettings(BaseSettings):
    """Redis configuration (future use)"""
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Environment-specific configurations
def get_development_overrides():
    """Development environment specific overrides"""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "reload": True,
        "hot_reload": True
    }


def get_production_overrides():
    """Production environment specific overrides"""
    return {
        "debug": False,
        "log_level": "INFO",
        "reload": False,
        "hot_reload": False,
        "workers": 4
    }


def get_test_overrides():
    """Test environment specific overrides"""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "environment": "test",
        "database_url": "sqlite:///./test.db"
    }