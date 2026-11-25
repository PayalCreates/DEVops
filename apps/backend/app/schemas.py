"""Pydantic request/response schemas (input validation lives here)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Role, TaskPriority, TaskStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth / users ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    # bcrypt truncates at 72 bytes, so cap length to avoid silent truncation.
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        checks = [any(c.isupper() for c in v), any(c.islower() for c in v),
                  any(c.isdigit() for c in v)]
        if not all(checks):
            raise ValueError("password must contain upper, lower case letters and a digit")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class UserOut(ORM):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class RoleUpdate(BaseModel):
    role: Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - not a secret
    expires_in: int
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


# ---------- Tasks ----------
class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class TaskOut(ORM):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class TaskPage(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    size: int


# ---------- Analytics ----------
class Analytics(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    overdue: int
    due_this_week: int
    completion_rate: float
    completed_last_7_days: list[dict[str, int | str]]


class HealthOut(BaseModel):
    status: str
    version: str
    color: str
    environment: str
    database: str | None = None
