from sqlalchemy.orm import Session

from app.domains.companies.repository import (
    add_recruiter_to_company,
    create_company,
    get_company_by_id,
    is_company_member,
    list_companies_for_recruiter,
)
from app.domains.companies.schemas import CompanyCreateRequest
from app.models.company import Company
from app.models.company_recruiter import CompanyRecruiter
from app.models.user import UserRole
from app.services.user_service import get_user_by_id


def create_owner_company(
    db: Session,
    *,
    owner_user_id: int,
    payload: CompanyCreateRequest,
) -> Company:
    return create_company(
        db,
        owner_user_id=owner_user_id,
        name=payload.name,
        website_url=payload.website_url,
        location=payload.location,
        description=payload.description,
    )


def list_owner_companies(db: Session, *, owner_user_id: int) -> list[Company]:
    return list_companies_for_recruiter(db, recruiter_user_id=owner_user_id)


def add_company_recruiter_member(
    db: Session,
    *,
    company_id: int,
    owner_user_id: int,
    recruiter_user_id: int,
) -> CompanyRecruiter:
    company = get_company_by_id(db, company_id=company_id)
    if company is None:
        raise ValueError("Company not found.")
    if company.owner_user_id != owner_user_id:
        raise PermissionError("Only company owner can add recruiters.")
    if recruiter_user_id == owner_user_id:
        raise ValueError("Owner is already a company recruiter.")
    recruiter = get_user_by_id(db, recruiter_user_id)
    if recruiter is None:
        raise ValueError("Recruiter user not found.")
    if recruiter.role != UserRole.RECRUITER:
        raise ValueError("User must have recruiter role.")
    if is_company_member(db, company_id=company_id, recruiter_user_id=recruiter_user_id):
        raise ValueError("Recruiter is already a company member.")

    return add_recruiter_to_company(
        db,
        company_id=company_id,
        recruiter_user_id=recruiter_user_id,
    )
