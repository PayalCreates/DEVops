"""Admin-only user management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Role, User
from app.schemas import RoleUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])
log = logging.getLogger(__name__)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and body.role != Role.ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot demote themselves")
    user.role = body.role
    db.commit()
    log.info("role_changed", extra={"target": user_id, "role": body.role.value, "by": admin.id})
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
def set_active(
    user_id: int,
    active: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot deactivate themselves")
    user.is_active = active
    db.commit()
    return user
