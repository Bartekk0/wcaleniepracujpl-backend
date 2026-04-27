from datetime import timedelta

from minio import Minio

from app.core.config import settings

client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def presigned_put_object(bucket_name: str, object_name: str, *, expires_seconds: int = 3600) -> str:
    return client.presigned_put_object(
        bucket_name,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )
