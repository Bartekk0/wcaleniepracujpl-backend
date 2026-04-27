from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int = 5432

    redis_host: str
    redis_port: int = 6379

    minio_root_user: str
    minio_root_password: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080

    database_url: str
    celery_broker_url: str
    celery_result_backend: str
    notifications_enabled: bool = True

    # Email: use ``log`` in development (no network). Set ``smtp`` with host/from for real delivery.
    email_transport: Literal["smtp", "log"] = "log"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
