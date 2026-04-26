from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_recruiter import CompanyRecruiter


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


def list_companies_for_recruiter(db: Session, *, recruiter_user_id: int) -> list[Company]:
    stmt = (
        select(Company)
        .outerjoin(
            CompanyRecruiter,
            CompanyRecruiter.company_id == Company.id,
        )
        .where(
            or_(
                Company.owner_user_id == recruiter_user_id,
                CompanyRecruiter.recruiter_user_id == recruiter_user_id,
            )
        )
        .order_by(Company.id.desc())
        .distinct()
    )
    return list(db.execute(stmt).scalars().all())


def get_company_by_id(db: Session, *, company_id: int) -> Company | None:
    stmt = select(Company).where(Company.id == company_id)
    return db.execute(stmt).scalar_one_or_none()


def is_company_member(db: Session, *, company_id: int, recruiter_user_id: int) -> bool:
    stmt = select(CompanyRecruiter.id).where(
        CompanyRecruiter.company_id == company_id,
        CompanyRecruiter.recruiter_user_id == recruiter_user_id,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def add_recruiter_to_company(
    db: Session,
    *,
    company_id: int,
    recruiter_user_id: int,
) -> CompanyRecruiter:
    membership = CompanyRecruiter(
        company_id=company_id,
        recruiter_user_id=recruiter_user_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership
