from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.db.session import get_db
from app.domains.companies.schemas import (
    CompanyCreateRequest,
    CompanyOut,
    CompanyRecruiterAddRequest,
    CompanyRecruiterOut,
)
from app.domains.companies.service import (
    add_company_recruiter_member,
    create_owner_company,
    list_owner_companies,
)
from app.models.user import User

router = APIRouter()


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company_endpoint(
    payload: CompanyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> CompanyOut:
    company = create_owner_company(
        db,
        owner_user_id=current_user.id,
        payload=payload,
    )
    return CompanyOut.model_validate(company)


@router.get("", response_model=list[CompanyOut])
def list_companies_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> list[CompanyOut]:
    companies = list_owner_companies(db, owner_user_id=current_user.id)
    return [CompanyOut.model_validate(company) for company in companies]


@router.post(
    "/{company_id}/recruiters",
    response_model=CompanyRecruiterOut,
    status_code=status.HTTP_201_CREATED,
)
def add_company_recruiter_endpoint(
    company_id: int,
    payload: CompanyRecruiterAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
) -> CompanyRecruiterOut:
    try:
        membership = add_company_recruiter_member(
            db,
            company_id=company_id,
            owner_user_id=current_user.id,
            recruiter_user_id=payload.recruiter_user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if message == "Company not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message in {
            "Recruiter is already a company member.",
            "Owner is already a company recruiter.",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return CompanyRecruiterOut.model_validate(membership)
