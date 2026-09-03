"""
Application Configuration Module

Manages all environment-based configuration settings using Pydantic Settings.
All sensitive values are loaded from environment variables with proper defaults.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Only load .env file if not in Docker (check for env_file override)
    model_config = SettingsConfigDict(
        env_file=".env" if not os.getenv("ENV_FILE") else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------------
    environment: str = Field(default="development", description="Application environment")
    app_name: str = Field(default="AI Lead Generation Platform", description="Application name")
    api_url: str = Field(default="http://localhost:8000", description="Backend API URL")
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL")

    # -----------------------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------------------
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT signing. Change in production!",
    )
    access_token_expire_minutes: int = Field(default=30, description="Access token TTL in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token TTL in days")
    encryption_key: str = Field(
        default="", description="Encryption key for sensitive data (32-byte base64)"
    )

    @field_validator("encryption_key", mode="before")
    def validate_encryption_key(cls, v):
        """Generate a default encryption key if not provided (dev only)."""
        if not v:
            import os

            env = os.getenv("ENVIRONMENT", "development")
            if env == "development":
                from cryptography.fernet import Fernet

                return Fernet.generate_key().decode()
        return v

    # -----------------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------------
    database_url: str = Field(
        default="mariadb+aiomysql://leadgen_user:leadgen_pass@db:3306/leadgen_db",
        description="Database connection URL (MariaDB 10.1.x compatible)",
    )
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Database pool max overflow")
    db_pool_timeout: int = Field(default=30, description="Database pool timeout in seconds")

    # -----------------------------------------------------------------------------
    # Redis
    # -----------------------------------------------------------------------------
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis connection URL")
    redis_cache_ttl: int = Field(default=3600, description="Default cache TTL in seconds")

    # -----------------------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:3000,http://frontend:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # -----------------------------------------------------------------------------
    # Email Providers - SMTP
    # -----------------------------------------------------------------------------
    smtp_host: str = Field(default="", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")

    # -----------------------------------------------------------------------------
    # Email Providers - Amazon SES
    # -----------------------------------------------------------------------------
    aws_access_key_id: str = Field(default="", description="AWS access key for SES")
    aws_secret_access_key: str = Field(default="", description="AWS secret key for SES")
    aws_region: str = Field(default="us-east-1", description="AWS region for SES")
    ses_sender_email: str = Field(default="", description="Verified SES sender email")

    # -----------------------------------------------------------------------------
    # Email Providers - Gmail API
    # -----------------------------------------------------------------------------
    gmail_client_id: str = Field(default="", description="Gmail OAuth2 client ID")
    gmail_client_secret: str = Field(default="", description="Gmail OAuth2 client secret")
    gmail_redirect_uri: str = Field(
        default="http://localhost:3000/auth/gmail/callback",
        description="Gmail OAuth2 redirect URI",
    )

    # -----------------------------------------------------------------------------
    # Email Providers - Microsoft Graph
    # -----------------------------------------------------------------------------
    microsoft_client_id: str = Field(default="", description="Microsoft OAuth2 client ID")
    microsoft_client_secret: str = Field(default="", description="Microsoft OAuth2 client secret")
    microsoft_tenant_id: str = Field(default="common", description="Microsoft tenant ID")
    microsoft_redirect_uri: str = Field(
        default="http://localhost:3000/auth/microsoft/callback",
        description="Microsoft OAuth2 redirect URI",
    )

    # -----------------------------------------------------------------------------
    # AI Providers - OpenAI
    # -----------------------------------------------------------------------------
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )

    # -----------------------------------------------------------------------------
    # AI Providers - Anthropic
    # -----------------------------------------------------------------------------
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic model to use"
    )

    # -----------------------------------------------------------------------------
    # Search Providers - Bing
    # -----------------------------------------------------------------------------
    bing_search_api_key: str = Field(default="", description="Bing Search API key")
    bing_search_endpoint: str = Field(
        default="https://api.bing.microsoft.com/v7.0/search",
        description="Bing Search API endpoint",
    )

    # -----------------------------------------------------------------------------
    # Search Providers - Google
    # -----------------------------------------------------------------------------
    google_search_api_key: str = Field(default="", description="Google Search API key")
    google_search_engine_id: str = Field(default="", description="Google Custom Search Engine ID")

    # -----------------------------------------------------------------------------
    # Search Providers - SerpAPI
    # -----------------------------------------------------------------------------
    serpapi_key: str = Field(default="", description="SerpAPI key")

    # -----------------------------------------------------------------------------
    # Search & Discovery
    # -----------------------------------------------------------------------------
    search_provider: str = Field(
        default="auto",
        description="Preferred search provider: auto, bing, google or serpapi",
    )
    search_results_per_keyword: int = Field(
        default=20, description="Maximum search results per keyword"
    )
    search_timeout: int = Field(default=30, description="Search provider request timeout (seconds)")
    search_max_retries: int = Field(default=2, description="Retries per search provider request")
    search_per_keyword_delay: float = Field(
        default=1.0, description="Delay between keyword searches (seconds)"
    )
    search_blocked_domains: str = Field(
        default="",
        description="Comma-separated extra domains to exclude from results "
        "(merged with the agent's built-in block list)",
    )

    # -----------------------------------------------------------------------------
    # Celery Configuration
    # -----------------------------------------------------------------------------
    celery_broker_url: str = Field(default="redis://redis:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(
        default="redis://redis:6379/0", description="Celery result backend"
    )
    celery_task_tracked: bool = Field(default=True, description="Track Celery tasks")
    celery_task_time_limit: int = Field(default=300, description="Celery task time limit (seconds)")
    celery_worker_prefetch_multiplier: int = Field(default=1, description="Celery worker prefetch")
    celery_worker_max_tasks_per_child: int = Field(
        default=100, description="Max tasks per Celery worker child"
    )

    # -----------------------------------------------------------------------------
    # Rate Limiting
    # -----------------------------------------------------------------------------
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")
    rate_limit_burst: int = Field(default=10, description="Rate limit burst size")

    # -----------------------------------------------------------------------------
    # Crawling Settings
    # -----------------------------------------------------------------------------
    crawler_user_agent: str = Field(
        default="AI-LeadGen-Bot/1.0 (+http://yourdomain.com/bot)",
        description="User agent for web crawler",
    )
    crawler_request_delay: float = Field(
        default=2.0, description="Delay between requests (seconds)"
    )
    crawler_max_pages_per_domain: int = Field(
        default=50, description="Max pages to crawl per domain"
    )
    crawler_timeout: int = Field(default=30, description="Request timeout in seconds")
    crawler_max_workers: int = Field(default=5, description="Maximum concurrent crawler workers")

    # -----------------------------------------------------------------------------
    # Email Sending Limits
    # -----------------------------------------------------------------------------
    default_daily_email_limit: int = Field(default=50, description="Default daily email limit")
    default_hourly_email_limit: int = Field(default=10, description="Default hourly email limit")
    default_emails_per_lead_days: int = Field(
        default=7, description="Days between emails to same lead"
    )

    # -----------------------------------------------------------------------------
    # File Handling
    # -----------------------------------------------------------------------------
    max_export_size: int = Field(default=100000, description="Maximum export file size (rows)")
    export_dir: str = Field(default="/app/exports", description="Export directory path")
    upload_dir: str = Field(default="/app/uploads", description="Upload directory path")

    # -----------------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="Application log level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: str = Field(default="/app/logs/app.log", description="Log file path")

    # -----------------------------------------------------------------------------
    # Monitoring
    # -----------------------------------------------------------------------------
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    statsd_host: str = Field(default="", description="StatsD host for metrics")
    statsd_port: int = Field(default=8125, description="StatsD port")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Cached application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
