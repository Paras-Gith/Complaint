from flask import Flask
from flask_limiter import Limiter

from complaint_app.routes.admin import register_admin_routes
from complaint_app.routes.auth import register_auth_routes
from complaint_app.routes.public import register_public_routes
from complaint_app.routes.student import register_student_routes


def register_routes(app: Flask, limiter: Limiter) -> None:
    register_public_routes(app)
    register_auth_routes(app, limiter)
    register_student_routes(app)
    register_admin_routes(app)
