import csv
import io
from collections.abc import Iterator
from typing import TypedDict

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from complaint_app.pagination import page_number
from complaint_app.security import admin_required
from complaint_app.services import complaint_counts_by_status, filtered_complaints
from config import Config
from models import (
    STATUSES,
    Alert,
    Complaint,
    StatusHistory,
    User,
    db,
)


class DashboardStats(TypedDict):
    total: int
    pending: int
    progress: int
    resolved: int
    students: int


def _safe_csv_cell(value: object | None) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def register_admin_routes(app: Flask) -> None:
    @app.get("/admin")
    @admin_required
    def admin_dashboard() -> ResponseReturnValue:
        counts = complaint_counts_by_status()
        by_category = (
            db.session.query(Complaint.category, func.count(Complaint.id))
            .group_by(Complaint.category)
            .all()
        )
        recent = (
            Complaint.query.options(joinedload(Complaint.student))
            .order_by(Complaint.created_at.desc())
            .limit(5)
            .all()
        )
        stats: DashboardStats = {
            "total": sum(counts.values()),
            "pending": counts.get("Pending", 0),
            "progress": counts.get("In Progress", 0),
            "resolved": counts.get("Resolved", 0),
            "students": User.query.filter_by(role="student").count(),
        }
        return render_template(
            "admin_dashboard.html",
            stats=stats,
            by_cat=by_category,
            recent=recent,
        )

    @app.get("/admin/complaints")
    @admin_required
    def admin_complaints() -> ResponseReturnValue:
        complaints_page = db.paginate(
            filtered_complaints(
                request.args.get("q", "").strip(),
                request.args.get("status", ""),
                request.args.get("category", ""),
                request.args.get("priority", ""),
            ),
            page=page_number(),
            per_page=current_app.config["PER_PAGE"],
            error_out=False,
        )
        return render_template(
            "admin_complaints.html",
            complaints=complaints_page.items,
            p=complaints_page,
            f=request.args,
        )

    @app.post("/admin/complaints/<int:cid>/update")
    @admin_required
    def update_complaint(cid: int) -> ResponseReturnValue:
        complaint = db.get_or_404(Complaint, cid)
        status = request.form["status"]
        remarks = request.form.get("remarks", "").strip()
        if status not in STATUSES:
            abort(400)
        complaint.status = status
        complaint.admin_remarks = remarks or complaint.admin_remarks
        db.session.add(
            StatusHistory(
                complaint_id=complaint.id,
                status=status,
                remarks=remarks or f"Status changed to {status}",
            )
        )
        db.session.commit()
        flash(f"Complaint #{complaint.id} updated to {status}.", "success")
        return redirect(request.referrer or url_for("admin_complaints"))

    @app.post("/admin/complaints/<int:cid>/delete")
    @admin_required
    def delete_complaint(cid: int) -> ResponseReturnValue:
        complaint = db.get_or_404(Complaint, cid)
        db.session.delete(complaint)
        db.session.commit()
        flash(f"Complaint #{cid} deleted.", "info")
        return redirect(url_for("admin_complaints"))

    @app.route("/admin/alerts", methods=["GET", "POST"])
    @admin_required
    def admin_alerts() -> ResponseReturnValue:
        if request.method == "POST":
            title = request.form["title"].strip()
            message = request.form["message"].strip()
            if title and message:
                db.session.add(Alert(title=title, message=message))
                db.session.commit()
                flash("Alert published.", "success")
            return redirect(url_for("admin_alerts"))
        alerts_page = db.paginate(
            db.select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()),
            page=page_number(),
            per_page=current_app.config["PER_PAGE"],
            error_out=False,
        )
        return render_template("admin_alerts.html", alerts=alerts_page.items, p=alerts_page)

    @app.post("/admin/alerts/<int:aid>/delete")
    @admin_required
    def delete_alert(aid: int) -> ResponseReturnValue:
        db.session.delete(db.get_or_404(Alert, aid))
        db.session.commit()
        return redirect(url_for("admin_alerts"))

    @app.get("/admin/students")
    @admin_required
    def admin_students() -> ResponseReturnValue:
        students_page = db.paginate(
            db.select(User).where(User.role == "student").order_by(User.created_at.desc()),
            page=page_number(),
            per_page=current_app.config["PER_PAGE"],
            error_out=False,
        )
        student_ids = [student.id for student in students_page.items]
        counts: dict[int, int] = {}
        if student_ids:
            counts = dict(
                db.session.query(Complaint.user_id, func.count(Complaint.id))
                .filter(Complaint.user_id.in_(student_ids))
                .group_by(Complaint.user_id)
                .all()
            )
        return render_template("admin_students.html", p=students_page, counts=counts)

    @app.get("/admin/report.csv")
    @admin_required
    def report_csv() -> Response:
        query = filtered_complaints(
            request.args.get("q", "").strip(),
            request.args.get("status", ""),
            request.args.get("category", ""),
            request.args.get("priority", ""),
        )

        def generate() -> Iterator[str]:
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer)

            def flush() -> str:
                output = buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
                return output

            writer.writerow(
                [
                    "ID",
                    "Student",
                    "Roll No",
                    "Department",
                    "Category",
                    "Priority",
                    "Title",
                    "Status",
                    "Submitted",
                    "Last Updated",
                    "Remarks",
                ]
            )
            yield flush()
            complaints = db.session.execute(
                query.execution_options(yield_per=Config.CSV_BATCH_SIZE)
            ).scalars()
            for row_number, complaint in enumerate(complaints, start=1):
                writer.writerow(
                    [
                        complaint.id,
                        _safe_csv_cell(complaint.student.name),
                        _safe_csv_cell(complaint.student.roll_no),
                        _safe_csv_cell(complaint.student.department),
                        complaint.category,
                        complaint.priority,
                        _safe_csv_cell(complaint.title),
                        complaint.status,
                        complaint.created_at.strftime("%Y-%m-%d %H:%M"),
                        complaint.updated_at.strftime("%Y-%m-%d %H:%M"),
                        _safe_csv_cell(complaint.admin_remarks),
                    ]
                )
                if row_number % Config.CSV_BATCH_SIZE == 0:
                    yield flush()
            remaining = flush()
            if remaining:
                yield remaining

        return Response(
            stream_with_context(generate()),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=complaint_report.csv"},
        )
