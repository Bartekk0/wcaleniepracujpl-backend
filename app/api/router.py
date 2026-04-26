from fastapi import APIRouter

from app.api.routes import auth, users
from app.domains.companies import router as companies_router

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
