from datetime import timedelta
import logging

from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)

client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket_exists() -> None:
    """Create the configured bucket if missing. Safe to call multiple times."""
    if not settings.minio_bootstrap_at_startup:
        logger.debug("MinIO bootstrap skipped (minio_bootstrap_at_startup=false).")
        return

    bucket = settings.minio_bucket
    try:
        if client.bucket_exists(bucket):
            logger.info("MinIO bucket exists: %s", bucket)
            return
        client.make_bucket(bucket)
        logger.info("MinIO bucket created: %s", bucket)
    except Exception:
        logger.exception(
            "MinIO bootstrap failed for bucket=%s (service continues without it).",
            bucket,
        )


def presigned_put_object(bucket_name: str, object_name: str, *, expires_seconds: int = 3600) -> str:
    return client.presigned_put_object(
        bucket_name,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )


def presigned_get_object(bucket_name: str, object_name: str, *, expires_seconds: int = 3600) -> str:
    return client.presigned_get_object(
        bucket_name,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )
