from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def now():
    """Naive UTC timestamp (datetime.utcnow is deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

CATEGORIES = ["Academic", "Hostel", "Library", "Canteen", "Infrastructure",
              "Transport", "Faculty", "Examination", "Other"]
PRIORITIES = ["Low", "Medium", "High"]
STATUSES = ["Pending", "In Progress", "Resolved"]


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    roll_no = db.Column(db.String(30))
    department = db.Column(db.String(80))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="student")  # student | admin
    created_at = db.Column(db.DateTime, default=now)
    complaints = db.relationship("Complaint", backref="student", lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Complaint(db.Model):
    __tablename__ = "complaints"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending", index=True)
    admin_remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now, index=True)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    history = db.relationship("StatusHistory", backref="complaint", lazy=True,
                              order_by="StatusHistory.changed_at",
                              cascade="all, delete-orphan")


class StatusHistory(db.Model):
    """Complaint history & tracking."""
    __tablename__ = "status_history"
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=now)


class Alert(db.Model):
    """System alerts / announcements published by admin."""
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now)



    