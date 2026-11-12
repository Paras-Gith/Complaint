import secrets
from functools import wraps
from typing import Callable, ParamSpec, TypedDict

from flask import Flask, Response, abort, current_app, flash, redirect, request, session, url_for
from flask.typing import ResponseReturnValue

from config import Config
from models import CATEGORIES, PRIORITIES, STATUSES, User, db

P = ParamSpec("P")


class TemplateGlobals(TypedDict):
    current_user: User | None
    csrf_token: Callable[[], str]
    STATUSES: list[str]
    CATEGORIES: list[str]
    PRIORITIES: list[str]
    asset_urls: dict[str, str]


CSP = (
    "default-src 'self'; "
    f"script-src 'self' {' '.join(Config.SCRIPT_CDN_ORIGINS)} 'unsafe-inline'; "
    f"style-src 'self' {' '.join(Config.STYLE_CDN_ORIGINS)} 'unsafe-inline'; "
    f"font-src 'self' {' '.join(Config.FONT_CDN_ORIGINS)}; "
    "img-src 'self' data:; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def current_user() -> User | None:
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if isinstance(user_id, int) else None


def csrf_token() -> str:
    token = session.get("_csrf")
    if not isinstance(token, str):
        token = secrets.token_hex(16)
        session["_csrf"] = token
    return token


def csrf_protect() -> None:
    if request.method == "POST":
        submitted_token = request.form.get("_csrf", "")
        session_token = session.get("_csrf", "")
        if (
            not submitted_token
            or not isinstance(session_token, str)
            or not secrets.compare_digest(submitted_token, session_token)
        ):
            abort(400)


def security_headers(response: Response) -> Response:
    headers = response.headers
    headers.setdefault("Content-Security-Policy", CSP)
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if current_app.config["SESSION_COOKIE_SECURE"]:
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if session.get("user_id"):
        headers["Cache-Control"] = "no-store"
    return response


def login_required(
    view: Callable[P, ResponseReturnValue],
) -> Callable[P, ResponseReturnValue]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        if current_user() is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def admin_required(
    view: Callable[P, ResponseReturnValue],
) -> Callable[P, ResponseReturnValue]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        user = current_user()
        if user is None:
            flash("Please log in as administrator.", "warning")
            return redirect(url_for("admin_login"))
        if user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def register_security(app: Flask) -> None:
    app.before_request(csrf_protect)
    app.after_request(security_headers)

    @app.context_processor
    def inject_globals() -> dict[str, object]:
        context: TemplateGlobals = {
            "current_user": current_user(),
            "csrf_token": csrf_token,
            "STATUSES": STATUSES,
            "CATEGORIES": CATEGORIES,
            "PRIORITIES": PRIORITIES,
            "asset_urls": Config.ASSET_URLS,
        }
        return dict(context)
