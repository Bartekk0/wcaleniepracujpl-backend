from fastapi import APIRouter

from app.schemas.auth import TokenPair

router = APIRouter()


@router.post("/login", response_model=TokenPair)
def login() -> TokenPair:
    return TokenPair(access_token="todo", refresh_token="todo")
