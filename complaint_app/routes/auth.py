from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from flask_limiter import Limiter

from complaint_app.services import weak_password
from config import Config
from models import User, db


def register_auth_routes(app: Flask, limiter: Limiter) -> None:
    def failed_login(response: Response) -> bool:
        return response.status_code == 200

    student_limit = (
        f"{Config.STUDENT_LOGIN_MAX_ATTEMPTS} per {Config.LOGIN_LIMIT_WINDOW_MINUTES} minutes"
    )
    admin_limit = (
        f"{Config.ADMIN_LOGIN_MAX_ATTEMPTS} per {Config.LOGIN_LIMIT_WINDOW_MINUTES} minutes"
    )

    @app.route("/register", methods=["GET", "POST"])
    def register() -> ResponseReturnValue:
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            problem = weak_password(password, email) if email else None
            if not name or not email:
                flash("Please fill in your name and email.", "danger")
            elif problem:
                flash(problem, "danger")
            elif User.query.filter_by(email=email).first():
                flash("An account with this email already exists.", "danger")
            else:
                user = User(
                    name=name,
                    email=email,
                    role="student",
                    roll_no=request.form.get("roll_no", "").strip(),
                    department=request.form.get("department", "").strip(),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit(student_limit, methods=["POST"], deduct_when=failed_login)
    def login() -> ResponseReturnValue:
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            user = User.query.filter_by(email=email, role="student").first()
            if user and user.check_password(request.form["password"]):
                session.clear()
                session["user_id"] = user.id
                flash(f"Welcome, {user.name}!", "success")
                return redirect(url_for("my_complaints"))
            flash("Invalid student email or password.", "danger")
        return render_template("login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    @limiter.limit(admin_limit, methods=["POST"], deduct_when=failed_login)
    def admin_login() -> ResponseReturnValue:
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            user = User.query.filter_by(email=email, role="admin").first()
            if user and user.check_password(request.form["password"]):
                session.clear()
                session["user_id"] = user.id
                flash("Welcome, Administrator!", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Invalid admin email or password.", "danger")
        return render_template("admin_login.html")

    @app.get("/logout")
    def logout() -> ResponseReturnValue:
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("index"))
