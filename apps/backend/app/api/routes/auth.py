"""Registration, login and current-user endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.metrics import LOGIN_ATTEMPTS
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Role, User
from app.schemas import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)
login_limiter = SlidingWindowLimiter(get_settings().login_rate_limit_per_minute)

# Pre-computed hash so login takes the same time whether or not the user exists
# (prevents user enumeration via timing).
_DUMMY_HASH = hash_password("timing-equaliser-Password1")


def _token_response(user: User) -> Token:
    settings = get_settings()
    token = create_access_token(str(user.id), user.role.value)
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)) -> Token:
    email = body.email.lower()
    # Hash BEFORE touching the database: bcrypt is ~250 ms of CPU and must not run
    # while holding a pooled connection (found via Locust: pool exhaustion at 100 users).
    hashed = hash_password(body.password)
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    # Self-registration always yields the least-privileged role.
    user = User(email=email, full_name=body.full_name, hashed_password=hashed, role=Role.USER)
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("user_registered", extra={"user_id": user.id})
    return _token_response(user)


@router.post("/login", response_model=Token)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    client = request.client.host if request.client else "unknown"
    if not login_limiter.allow(f"{client}:{body.email.lower()}"):
        LOGIN_ATTEMPTS.labels("rate_limited").inc()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts")

    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    snapshot = UserOut.model_validate(user) if user else None
    stored_hash = user.hashed_password if user else _DUMMY_HASH
    # End the read transaction -> connection goes back to the pool before the
    # CPU-heavy bcrypt check (same pool-exhaustion fix as /register).
    db.rollback()
    valid = verify_password(body.password, stored_hash)
    if snapshot is None or not valid or not snapshot.is_active:
        LOGIN_ATTEMPTS.labels("failure").inc()
        log.warning("login_failed", extra={"client": client})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    LOGIN_ATTEMPTS.labels("success").inc()
    log.info("login_success", extra={"user_id": snapshot.id})
    settings = get_settings()
    return Token(access_token=create_access_token(str(snapshot.id), snapshot.role.value),
                 expires_in=settings.access_token_expire_minutes * 60, user=snapshot)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
