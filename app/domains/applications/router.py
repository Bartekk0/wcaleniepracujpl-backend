from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.api.deps import require_candidate, require_recruiter, require_roles
from app.db.session import get_db
from app.domains.applications.cv_presign import presigned_upload_cv
from app.domains.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationEventOut,
    ApplicationOut,
    ApplicationStatusUpdateRequest,
    CvDownloadPresignResponse,
    CvPresignRequest,
    CvPresignResponse,
)
from app.domains.applications.service import (
    apply_to_job,
    change_application_status,
    get_application_history,
    list_my_applications,
    list_recruiter_applications_for_job,
    presign_application_cv_download,
)
from app.models.application import ApplicationStatus
from app.models.user import User, UserRole

router = APIRouter()


def _parse_application_status_query(status_value: str | None) -> ApplicationStatus | None:
    if status_value is None:
        return None
    try:
        return ApplicationStatus(status_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid status value: {status_value}.",
        ) from exc


@router.post("", response_model=ApplicationOut, status_code=http_status.HTTP_201_CREATED)
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
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message == "Job is not published.":
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message == "Application already exists for this job.":
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return ApplicationOut.model_validate(application)


@router.post("/cv-presign", response_model=CvPresignResponse)
def presign_cv_upload_endpoint(
    payload: CvPresignRequest,
    current_user: User = Depends(require_candidate),
) -> CvPresignResponse:
    object_key, upload_url, expires = presigned_upload_cv(
        candidate_user_id=current_user.id,
        filename=payload.filename,
    )
    return CvPresignResponse(
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=expires,
    )


@router.get("/{application_id}/cv-download", response_model=CvDownloadPresignResponse)
def presign_cv_download_endpoint(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CANDIDATE, UserRole.RECRUITER, UserRole.ADMIN)
    ),
) -> CvDownloadPresignResponse:
    try:
        download_url, expires = presign_application_cv_download(
            db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            application_id=application_id,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Application not found.":
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message == "No CV uploaded for this application.":
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return CvDownloadPresignResponse(
        download_url=download_url,
        expires_in_seconds=expires,
    )


@router.get("/me", response_model=list[ApplicationOut])
def list_my_applications_endpoint(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
) -> list[ApplicationOut]:
    parsed_status = _parse_application_status_query(status)
    applications = list_my_applications(
        db,
        candidate_user_id=current_user.id,
        status=parsed_status,
    )
    return [ApplicationOut.model_validate(application) for application in applications]


@router.get("/jobs/{job_id}", response_model=list[ApplicationOut])
def list_job_applications_endpoint(
    job_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> list[ApplicationOut]:
    parsed_status = _parse_application_status_query(status)
    try:
        applications = list_recruiter_applications_for_job(
            db,
            recruiter_user_id=current_user.id,
            job_id=job_id,
            status=parsed_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return [ApplicationOut.model_validate(application) for application in applications]


@router.patch("/{application_id}/status", response_model=ApplicationOut)
def update_application_status_endpoint(
    application_id: int,
    payload: ApplicationStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
) -> ApplicationOut:
    try:
        application = change_application_status(
            db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            application_id=application_id,
            new_status=payload.status,
        )
    except ValueError as exc:
        message = str(exc)
        if message in {"Application not found.", "Job not found."}:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=message) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ApplicationOut.model_validate(application)


@router.get("/{application_id}/history", response_model=list[ApplicationEventOut])
def application_history_endpoint(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CANDIDATE, UserRole.RECRUITER, UserRole.ADMIN)
    ),
) -> list[ApplicationEventOut]:
    try:
        events = get_application_history(
            db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            application_id=application_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return [ApplicationEventOut.model_validate(event) for event in events]
