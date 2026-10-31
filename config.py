import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
    # MySQL (as per synopsis). Edit user/password/db name, or set DATABASE_URL env var.
    # For quick local testing without MySQL: DATABASE_URL=sqlite:///complaints.db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost/complaint_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@college.edu")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
