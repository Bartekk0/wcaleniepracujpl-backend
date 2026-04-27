"""Presigned uploads for candidate CV objects stored in MinIO."""

from __future__ import annotations

import re
import uuid

from app.core.config import settings
from app.storage.minio_client import presigned_get_object, presigned_put_object

_SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_upload_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1]
    cleaned = _SAFE_FILENAME.sub("_", base)
    return (cleaned or "cv.bin")[:200]


def build_cv_object_key(*, candidate_user_id: int, filename: str) -> str:
    return f"cv/{candidate_user_id}/{uuid.uuid4().hex}_{sanitize_upload_filename(filename)}"


def validate_cv_object_key(*, candidate_user_id: int, object_key: str | None) -> None:
    if object_key is None:
        return
    prefix = f"cv/{candidate_user_id}/"
    if not object_key.startswith(prefix):
        raise ValueError("CV object key is invalid for this candidate.")
    if len(object_key) > 512:
        raise ValueError("CV object key is too long.")


def presigned_upload_cv(*, candidate_user_id: int, filename: str) -> tuple[str, str, int]:
    object_key = build_cv_object_key(candidate_user_id=candidate_user_id, filename=filename)
    expires = 3600
    upload_url = presigned_put_object(
        settings.minio_bucket,
        object_key,
        expires_seconds=expires,
    )
    return object_key, upload_url, expires


def presigned_download_cv(*, object_key: str) -> tuple[str, int]:
    expires = 3600
    download_url = presigned_get_object(
        settings.minio_bucket,
        object_key,
        expires_seconds=expires,
    )
    return download_url, expires
