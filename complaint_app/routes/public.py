from flask import Flask, current_app, render_template
from flask.typing import ResponseReturnValue

from complaint_app.pagination import page_number
from models import Alert, db


def register_public_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> ResponseReturnValue:
        alerts = Alert.query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(3).all()
        return render_template("index.html", alerts=alerts)

    @app.get("/alerts")
    def alerts() -> ResponseReturnValue:
        alerts_page = db.paginate(
            db.select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()),
            page=page_number(),
            per_page=current_app.config["PER_PAGE"],
            error_out=False,
        )
        return render_template("alerts.html", alerts=alerts_page.items, p=alerts_page)
