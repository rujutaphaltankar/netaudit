from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.audit import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login", 10, 60))])
def login(body: LoginRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.username) == body.username.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise AppError(401, "invalid_credentials", "Invalid username or password.")
    token = create_access_token(user.id, user.role, settings.jwt_secret, settings.jwt_expire_minutes)
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
