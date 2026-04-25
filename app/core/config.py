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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
