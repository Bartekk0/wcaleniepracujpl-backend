from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


def create_company(
    db: Session,
    *,
    owner_user_id: int,
    name: str,
    website_url: str | None = None,
    location: str | None = None,
    description: str | None = None,
) -> Company:
    company = Company(
        owner_user_id=owner_user_id,
        name=name,
        website_url=website_url,
        location=location,
        description=description,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def list_companies_by_owner(db: Session, *, owner_user_id: int) -> list[Company]:
    stmt = (
        select(Company)
        .where(Company.owner_user_id == owner_user_id)
        .order_by(Company.id.desc())
    )
    return list(db.execute(stmt).scalars().all())
