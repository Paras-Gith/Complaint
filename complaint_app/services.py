from flask import current_app
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import contains_eager

from models import (
    CATEGORIES,
    PRIORITIES,
    STATUSES,
    Complaint,
    User,
    db,
)

COMMON_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "12345678",
    "123456789",
    "qwerty123",
    "qwertyuiop",
    "iloveyou",
    "11111111",
    "abcd1234",
    "admin123",
    "college123",
}


def seed_admin() -> None:
    if not User.query.filter_by(role="admin").first():
        admin = User(
            name="Administrator",
            email=current_app.config["ADMIN_EMAIL"],
            role="admin",
        )
        admin.set_password(current_app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()


def weak_password(password: str, email: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.lower() in COMMON_PASSWORDS or password.isdigit() or len(set(password)) < 4:
        return "That password is too easy to guess. Mix letters and numbers."
    local_part = email.split("@", maxsplit=1)[0]
    if len(local_part) >= 3 and local_part in password.lower():
        return "Password must not contain your email name."
    return None


def filtered_complaints(
    search: str,
    status: str,
    category: str,
    priority: str,
) -> Select[tuple[Complaint]]:
    query = select(Complaint).join(User).options(contains_eager(Complaint.student))
    if search:
        like = f"%{search}%"
        conditions = [
            Complaint.title.like(like),
            Complaint.description.like(like),
            User.name.like(like),
            User.roll_no.like(like),
        ]
        if search.isdigit():
            conditions.append(Complaint.id == int(search))
        query = query.where(or_(*conditions))
    if status in STATUSES:
        query = query.where(Complaint.status == status)
    if category in CATEGORIES:
        query = query.where(Complaint.category == category)
    if priority in PRIORITIES:
        query = query.where(Complaint.priority == priority)
    return query.order_by(Complaint.created_at.desc(), Complaint.id.desc())


def complaint_counts_by_status() -> dict[str, int]:
    return dict(
        db.session.query(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
