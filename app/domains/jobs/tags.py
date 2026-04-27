from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_tag import JobTag

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_tag_slug(raw: str) -> str:
    s = raw.strip().lower().replace("_", "-")
    if not _SLUG_RE.fullmatch(s):
        raise ValueError(f"Invalid tag slug: {raw!r}")
    return s


def get_or_create_tags(db: Session, slugs: list[str]) -> list[JobTag]:
    tags: list[JobTag] = []
    seen: set[str] = set()
    for raw in slugs:
        slug = normalize_tag_slug(raw)
        if slug in seen:
            continue
        seen.add(slug)
        stmt = select(JobTag).where(JobTag.slug == slug)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            tags.append(existing)
            continue
        label = raw.strip()
        tag = JobTag(slug=slug, label=label[:120])
        try:
            with db.begin_nested():
                db.add(tag)
                db.flush()
        except IntegrityError:
            db.expunge(tag)
            winner = db.execute(select(JobTag).where(JobTag.slug == slug)).scalar_one_or_none()
            if winner is None:
                raise
            tags.append(winner)
            continue
        tags.append(tag)
    return tags


def replace_job_tags(db: Session, *, job_id: int, tag_slugs: list[str]) -> None:
    job = db.get(Job, job_id)
    if job is None:
        return
    if not tag_slugs:
        job.tags = []
        db.commit()
        db.refresh(job)
        return
    tags = get_or_create_tags(db, tag_slugs)
    job.tags = tags
    db.commit()
    db.refresh(job)
