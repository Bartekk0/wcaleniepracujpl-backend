from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_candidate, require_recruiter
from app.db.session import get_db
from app.domains.applications.schemas import ApplicationCreateRequest, ApplicationOut
from app.domains.applications.service import (
    apply_to_job,
    list_my_applications,
    list_recruiter_applications_for_job,
)
from app.models.user import User

router = APIRouter()


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_to_job_endpoint(
    payload: ApplicationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
) -> ApplicationOut:
    try:
        application = apply_to_job(
            db,
            candidate_user_id=current_user.id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Job not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message == "Application already exists for this job.":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return ApplicationOut.model_validate(application)


@router.get("/me", response_model=list[ApplicationOut])
def list_my_applications_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
) -> list[ApplicationOut]:
    applications = list_my_applications(db, candidate_user_id=current_user.id)
    return [ApplicationOut.model_validate(application) for application in applications]


@router.get("/jobs/{job_id}", response_model=list[ApplicationOut])
def list_job_applications_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> list[ApplicationOut]:
    try:
        applications = list_recruiter_applications_for_job(
            db,
            recruiter_user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return [ApplicationOut.model_validate(application) for application in applications]
