"""Authentication / authorization dependencies."""
from __future__ import annotations

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if creds is None:
        raise AppError(401, "not_authenticated", "Authentication required.")
    try:
        payload = decode_access_token(creds.credentials, settings.jwt_secret)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError):
        raise AppError(401, "invalid_token", "Invalid or expired token.") from None
    if user is None or not user.is_active:
        raise AppError(401, "invalid_token", "Invalid or expired token.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(403, "forbidden", "This action requires the admin role.")
    return user
