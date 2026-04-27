from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.db.session import get_db
from app.domains.jobs.schemas import JobCreateRequest, JobListQueryParams, JobOut
from app.domains.jobs.service import (
    create_recruiter_job,
    get_public_job,
    list_public_jobs,
    list_recruiter_jobs,
)
from app.models.user import User

router = APIRouter()


def job_list_query_params(
    company_id: int | None = Query(None),
    title_query: str | None = Query(None),
    location: str | None = Query(None),
    employment_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: list[str] | None = Query(None),
) -> JobListQueryParams:
    try:
        return JobListQueryParams(
            company_id=company_id,
            title_query=title_query,
            location=location,
            employment_type=employment_type,
            tags=list(tag) if tag else [],
            page=page,
            page_size=page_size,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job_endpoint(
    payload: JobCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> JobOut:
    try:
        job = create_recruiter_job(
            db,
            recruiter_user_id=current_user.id,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
def list_jobs_endpoint(
    query: Annotated[JobListQueryParams, Depends(job_list_query_params)],
    db: Session = Depends(get_db),
) -> list[JobOut]:
    jobs = list_public_jobs(db, query=query)
    return [JobOut.model_validate(job) for job in jobs]


@router.get("/me", response_model=list[JobOut])
def list_recruiter_jobs_endpoint(
    query: Annotated[JobListQueryParams, Depends(job_list_query_params)],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> list[JobOut]:
    jobs = list_recruiter_jobs(db, recruiter_user_id=current_user.id, query=query)
    return [JobOut.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobOut)
def detail_job_endpoint(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = get_public_job(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return JobOut.model_validate(job)
