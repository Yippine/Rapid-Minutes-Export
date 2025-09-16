from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application Configuration
    app_name: str = Field(default="Rapid-Minutes-Export", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=True, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Ollama Configuration
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field(default="Yu-Feng/Llama-3.1-TAIDE-LX-8B-Chat:Q4_K_M", env="OLLAMA_MODEL")  # TAIDE model for Traditional Chinese
    ollama_timeout: int = Field(default=300, env="OLLAMA_TIMEOUT")  # 5 minutes for 8B model
    ollama_max_retries: int = Field(default=3, env="OLLAMA_MAX_RETRIES")
    
    # File Paths Configuration
    templates_dir: str = Field(default="./templates", env="TEMPLATES_DIR")
    data_dir: str = Field(default="./data", env="DATA_DIR")
    input_dir: str = Field(default="./data/input", env="INPUT_DIR")
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    output_dir: str = Field(default="./data/output", env="OUTPUT_DIR")
    temp_dir: str = Field(default="./data/temp", env="TEMP_DIR")
    static_dir: str = Field(default="./static", env="STATIC_DIR")
    
    # File Processing Configuration  
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(default=".txt", env="ALLOWED_FILE_TYPES")
    upload_timeout_seconds: int = Field(default=30, env="UPLOAD_TIMEOUT_SECONDS")
    processing_timeout_seconds: int = Field(default=300, env="PROCESSING_TIMEOUT_SECONDS")
    cleanup_interval: int = Field(default=3600, env="CLEANUP_INTERVAL")
    
    # Document Generation Configuration
    default_template: str = Field(default="default_meeting.docx", env="DEFAULT_TEMPLATE")
    word_template_dir: str = Field(default="./templates/word", env="WORD_TEMPLATE_DIR")
    pdf_output_quality: str = Field(default="high", env="PDF_OUTPUT_QUALITY")
    document_author: str = Field(default="Rapid-Minutes-Export", env="DOCUMENT_AUTHOR")
    
    # API Configuration
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000", env="CORS_ORIGINS")
    max_request_size_mb: int = Field(default=15, env="MAX_REQUEST_SIZE_MB")
    
    # Security Configuration
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS")
    trust_host_header: bool = Field(default=False, env="TRUST_HOST_HEADER")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", env="LOG_FILE")
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
    
    # Legacy compatibility
    upload_max_size: int = Field(default=10485760)  # Computed from max_file_size_mb
    max_processing_time: int = Field(default=300)   # Alias for processing_timeout_seconds
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set computed fields
        self.upload_max_size = self.max_file_size_mb * 1024 * 1024
        self.max_processing_time = self.processing_timeout_seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of forbidding them


@lru_cache()
def get_settings() -> Settings:
    return Settings()