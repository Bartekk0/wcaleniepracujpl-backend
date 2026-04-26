from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.db.session import get_db
from app.domains.companies.schemas import CompanyCreateRequest, CompanyOut
from app.domains.companies.service import create_owner_company, list_owner_companies
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
