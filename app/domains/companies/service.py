from sqlalchemy.orm import Session

from app.domains.companies.repository import create_company, list_companies_by_owner
from app.domains.companies.schemas import CompanyCreateRequest
from app.models.company import Company


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
    return list_companies_by_owner(db, owner_user_id=owner_user_id)
