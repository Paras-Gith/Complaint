from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue

from complaint_app.pagination import page_number
from complaint_app.security import current_user, login_required
from models import (
    CATEGORIES,
    PRIORITIES,
    STATUSES,
    Complaint,
    StatusHistory,
    db,
)


def register_student_routes(app: Flask) -> None:
    @app.route("/complaints/new", methods=["GET", "POST"])
    @login_required
    def new_complaint() -> ResponseReturnValue:
        user = current_user()
        if user is None or user.role != "student":
            abort(403)
        if request.method == "POST":
            title = request.form["title"].strip()
            description = request.form["description"].strip()
            category = request.form["category"]
            priority = request.form["priority"]
            if (
                not title
                or not description
                or category not in CATEGORIES
                or priority not in PRIORITIES
            ):
                flash("Please complete the form correctly.", "danger")
            else:
                complaint = Complaint(
                    user_id=user.id,
                    title=title,
                    description=description,
                    category=category,
                    priority=priority,
                )
                db.session.add(complaint)
                db.session.flush()
                db.session.add(
                    StatusHistory(
                        complaint_id=complaint.id,
                        status="Pending",
                        remarks="Complaint submitted",
                    )
                )
                db.session.commit()
                flash(f"Complaint #{complaint.id} submitted successfully.", "success")
                return redirect(url_for("complaint_detail", cid=complaint.id))
        return render_template("new_complaint.html")

    @app.get("/my-complaints")
    @login_required
    def my_complaints() -> ResponseReturnValue:
        user = current_user()
        if user is None:
            abort(403)
        status = request.args.get("status", "")
        query = db.select(Complaint).where(Complaint.user_id == user.id)
        if status in STATUSES:
            query = query.where(Complaint.status == status)
        complaints_page = db.paginate(
            query.order_by(Complaint.created_at.desc(), Complaint.id.desc()),
            page=page_number(),
            per_page=current_app.config["PER_PAGE"],
            error_out=False,
        )
        return render_template(
            "my_complaints.html",
            complaints=complaints_page.items,
            status=status,
            p=complaints_page,
        )

    @app.get("/complaints/<int:cid>")
    @login_required
    def complaint_detail(cid: int) -> ResponseReturnValue:
        complaint = db.get_or_404(Complaint, cid)
        user = current_user()
        if user is None or (user.role != "admin" and complaint.user_id != user.id):
            abort(403)
        return render_template("complaint_detail.html", c=complaint)
