"""Dashboard analytics for the current user (or everyone, for managers/admins)."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import can_see_all_tasks, get_current_user
from app.db.session import get_db
from app.models import Task, TaskPriority, TaskStatus, User
from app.schemas import Analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=Analytics)
def summary(all_users: bool = False, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)) -> Analytics:
    scope = [] if (all_users and can_see_all_tasks(user)) else [Task.owner_id == user.id]

    def count(*conds) -> int:
        return db.scalar(select(func.count(Task.id)).where(*scope, *conds)) or 0

    by_status = {s.value: count(Task.status == s) for s in TaskStatus}
    by_priority = {p.value: count(Task.priority == p) for p in TaskPriority}
    total = sum(by_status.values())
    today = date.today()
    open_ = Task.status != TaskStatus.DONE
    overdue = count(open_, Task.due_date < today)
    due_week = count(open_, Task.due_date >= today, Task.due_date <= today + timedelta(days=7))

    since = datetime.now(UTC) - timedelta(days=6)
    rows = db.scalars(select(Task.completed_at).where(
        *scope, Task.completed_at.is_not(None), Task.completed_at >= since.replace(
            hour=0, minute=0, second=0, microsecond=0))).all()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(6, -1, -1)}
    for ts in rows:
        key = ts.date().isoformat()
        if key in buckets:
            buckets[key] += 1

    return Analytics(
        total=total,
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        due_this_week=due_week,
        completion_rate=round(by_status["done"] / total * 100, 1) if total else 0.0,
        completed_last_7_days=[{"date": d, "count": c} for d, c in buckets.items()],
    )
