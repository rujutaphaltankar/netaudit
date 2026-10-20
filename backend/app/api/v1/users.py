from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.audit import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.username) == body.username.lower())):
        raise AppError(409, "username_taken", "That username already exists.")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "User not found.")
    if user.id == admin.id:
        raise AppError(400, "cannot_modify_self", "You cannot change your own role or active status.")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    db.commit()
    return user
