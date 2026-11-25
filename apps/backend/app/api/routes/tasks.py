"""Task CRUD with ownership checks, filtering, search, sorting and pagination."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import can_see_all_tasks, get_current_user
from app.core.metrics import TASKS_CREATED
from app.db.session import get_db
from app.models import Task, TaskPriority, TaskStatus, User
from app.schemas import TaskCreate, TaskOut, TaskPage, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

SORTABLE = {
    "created_at": Task.created_at,
    "due_date": Task.due_date,
    "priority": Task.priority,
    "title": Task.title,
    "status": Task.status,
}


def _get_owned_task(db: Session, task_id: int, user: User) -> Task:
    task = db.get(Task, task_id)
    # Return 404 (not 403) for other users' tasks so IDs can't be probed.
    if task is None or (task.owner_id != user.id and not can_see_all_tasks(user)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def _apply_completion(task: Task) -> None:
    if task.status == TaskStatus.DONE and task.completed_at is None:
        task.completed_at = datetime.now(UTC)
    elif task.status != TaskStatus.DONE:
        task.completed_at = None


@router.get("", response_model=TaskPage)
def list_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = None,
    q: str | None = Query(default=None, max_length=100),
    sort: str = Query(default="created_at"),
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    all_users: bool = False,
) -> TaskPage:
    stmt = select(Task)
    if not (all_users and can_see_all_tasks(user)):
        stmt = stmt.where(Task.owner_id == user.id)
    if status_:
        stmt = stmt.where(Task.status == status_)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Task.title).like(like),
                              func.lower(Task.description).like(like)))
    if sort not in SORTABLE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"sort must be one of {list(SORTABLE)}")

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    col = SORTABLE[sort]
    stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), Task.id.desc())
    items = db.scalars(stmt.offset((page - 1) * size).limit(size)).all()
    return TaskPage(items=[TaskOut.model_validate(t) for t in items], total=total,
                    page=page, size=size)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> Task:
    task = Task(**body.model_dump(), owner_id=user.id)
    _apply_completion(task)
    db.add(task)
    db.commit()
    db.refresh(task)
    TASKS_CREATED.inc()
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)) -> Task:
    return _get_owned_task(db, task_id, user)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> Task:
    task = _get_owned_task(db, task_id, user)
    data = body.model_dump(exclude_unset=True)
    if "title" in data and (data["title"] is None or not data["title"].strip()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "title must not be blank")
    for field in ("status", "priority"):
        if field in data and data[field] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field} cannot be null")
    for k, v in data.items():
        setattr(task, k, v.strip() if k == "title" else v)
    _apply_completion(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> Response:
    task = _get_owned_task(db, task_id, user)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
