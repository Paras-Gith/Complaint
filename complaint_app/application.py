from flask import Flask, render_template
from flask.typing import ResponseReturnValue
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from complaint_app.routes import register_routes
from complaint_app.security import register_security
from complaint_app.services import seed_admin
from config import Config
from models import db


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config)
    db.init_app(app)

    limiter = Limiter(
        get_remote_address,
        storage_uri=app.config["RATE_LIMIT_STORAGE_URI"],
    )
    limiter.init_app(app)

    register_security(app)
    register_routes(app, limiter)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()
        seed_admin()

    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(429)
    def too_many(_error: Exception) -> ResponseReturnValue:
        return (
            render_template(
                "error.html",
                code=429,
                msg=(
                    "Too many failed login attempts. Wait "
                    f"{app.config['LOGIN_LIMIT_WINDOW_MINUTES']} minutes and try again."
                ),
            ),
            429,
        )

    @app.errorhandler(400)
    def bad_request(_error: Exception) -> ResponseReturnValue:
        return (
            render_template(
                "error.html",
                code=400,
                msg=(
                    "Your session expired or the form was invalid. "
                    "Go back, reload the page and try again."
                ),
            ),
            400,
        )

    @app.errorhandler(403)
    def forbidden(_error: Exception) -> ResponseReturnValue:
        return render_template(
            "error.html", code=403, msg="You don't have access to this page."
        ), 403

    @app.errorhandler(404)
    def not_found(_error: Exception) -> ResponseReturnValue:
        return render_template("error.html", code=404, msg="Page not found."), 404
