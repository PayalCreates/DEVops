"""Idempotent seed: bootstrap admin (from env) + optional sample data.

Usage:
    python -m app.seed                # admin only
    python -m app.seed --sample-data  # admin + demo users + sample tasks
"""

import argparse
import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, Task, TaskPriority, TaskStatus, User

log = logging.getLogger("seed")
SAMPLE_FILE = Path(os.getenv("SEED_FILE", Path(__file__).parent / "sample_data.json"))


def _get_or_create_user(db, email: str, name: str, password: str, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, full_name=name, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.flush()
    log.info("seeded user %s (%s)", email, role.value)
    return user


def seed(sample: bool) -> None:
    s = get_settings()
    with SessionLocal() as db:
        if s.admin_email and s.admin_password:
            _get_or_create_user(db, s.admin_email.lower(), "Platform Admin", s.admin_password,
                                Role.ADMIN)
        else:
            log.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping admin bootstrap")

        if sample:
            data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
            demo_pw = os.getenv("DEMO_USER_PASSWORD")
            if not demo_pw:
                raise SystemExit("DEMO_USER_PASSWORD must be set to seed demo users")
            for u in data["users"]:
                user = _get_or_create_user(db, u["email"], u["full_name"], demo_pw, Role(u["role"]))
                if db.scalar(select(Task.id).where(Task.owner_id == user.id).limit(1)):
                    continue  # idempotent: user already has tasks
                for t in data["tasks"]:
                    if t["owner"] != u["email"]:
                        continue
                    task = Task(
                        title=t["title"], description=t.get("description"),
                        status=TaskStatus(t["status"]), priority=TaskPriority(t["priority"]),
                        due_date=date.today() + timedelta(days=t["due_in_days"])
                        if t.get("due_in_days") is not None else None,
                        owner_id=user.id,
                    )
                    if task.status == TaskStatus.DONE:
                        from datetime import UTC, datetime
                        task.completed_at = datetime.now(UTC) - timedelta(
                            days=t.get("completed_days_ago", 0))
                    db.add(task)
        db.commit()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    p = argparse.ArgumentParser()
    p.add_argument("--sample-data", action="store_true")
    seed(p.parse_args().sample_data)
