import csv
import io
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, Response, abort)
from sqlalchemy import or_, func

from config import Config
from models import (db, User, Complaint, StatusHistory, Alert,
                    CATEGORIES, PRIORITIES, STATUSES)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ---------- helpers ----------
def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


@app.context_processor
def inject_globals():
    return dict(current_user=current_user(), STATUSES=STATUSES,
                CATEGORIES=CATEGORIES, PRIORITIES=PRIORITIES)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user():
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        u = current_user()
        if not u:
            flash("Please log in as administrator.", "warning")
            return redirect(url_for("admin_login"))
        if u.role != "admin":
            abort(403)
        return f(*a, **kw)
    return wrapper


def seed_admin():
    if not User.query.filter_by(role="admin").first():
        admin = User(name="Administrator", email=Config.ADMIN_EMAIL, role="admin")
        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()


# ---------- public / auth ----------
@app.route("/")
def index():
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(3).all()
    return render_template("index.html", alerts=alerts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if not name or not email or len(pw) < 6:
            flash("Fill all fields; password must be at least 6 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
        else:
            u = User(name=name, email=email, role="student",
                     roll_no=request.form.get("roll_no", "").strip(),
                     department=request.form.get("department", "").strip())
            u.set_password(pw)
            db.session.add(u)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Student login."""
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        u = User.query.filter_by(email=email, role="student").first()
        if u and u.check_password(request.form["password"]):
            session.clear()
            session["user_id"] = u.id
            flash(f"Welcome, {u.name}!", "success")
            return redirect(url_for("my_complaints"))
        flash("Invalid student email or password.", "danger")
    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Administrator login (separate from student login)."""
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        u = User.query.filter_by(email=email, role="admin").first()
        if u and u.check_password(request.form["password"]):
            session.clear()
            session["user_id"] = u.id
            flash("Welcome, Administrator!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin email or password.", "danger")
    return render_template("admin_login.html")
    
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ---------- student ----------
@app.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    u = current_user()
    if u.role != "student":
        abort(403)
    if request.method == "POST":
        title = request.form["title"].strip()
        desc = request.form["description"].strip()
        category = request.form["category"]
        priority = request.form["priority"]
        if not title or not desc or category not in CATEGORIES or priority not in PRIORITIES:
            flash("Please complete the form correctly.", "danger")
        else:
            c = Complaint(user_id=u.id, title=title, description=desc,
                          category=category, priority=priority)
            db.session.add(c)
            db.session.flush()
            db.session.add(StatusHistory(complaint_id=c.id, status="Pending",
                                         remarks="Complaint submitted"))
            db.session.commit()
            flash(f"Complaint #{c.id} submitted successfully.", "success")
            return redirect(url_for("complaint_detail", cid=c.id))
    return render_template("new_complaint.html")


@app.route("/my-complaints")
@login_required
def my_complaints():
    u = current_user()
    q = Complaint.query.filter_by(user_id=u.id)
    status = request.args.get("status", "")
    if status in STATUSES:
        q = q.filter_by(status=status)
    complaints = q.order_by(Complaint.created_at.desc()).all()
    return render_template("my_complaints.html", complaints=complaints, status=status)


@app.route("/complaints/<int:cid>")
@login_required
def complaint_detail(cid):
    c = db.get_or_404(Complaint, cid)
    u = current_user()
    if u.role != "admin" and c.user_id != u.id:
        abort(403)
    return render_template("complaint_detail.html", c=c)


@app.route("/alerts")
def alerts():
    items = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template("alerts.html", alerts=items)


# ---------- admin ----------
@app.route("/admin")
@admin_required
def admin_dashboard():
    counts = dict(db.session.query(Complaint.status, func.count(Complaint.id))
                  .group_by(Complaint.status).all())
    by_cat = (db.session.query(Complaint.category, func.count(Complaint.id))
              .group_by(Complaint.category).all())
    recent = Complaint.query.order_by(Complaint.created_at.desc()).limit(5).all()
    stats = {
        "total": sum(counts.values()),
        "pending": counts.get("Pending", 0),
        "progress": counts.get("In Progress", 0),
        "resolved": counts.get("Resolved", 0),
        "students": User.query.filter_by(role="student").count(),
    }
    return render_template("admin_dashboard.html", stats=stats, by_cat=by_cat, recent=recent)


def filtered_query():
    q = Complaint.query.join(User)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    category = request.args.get("category", "")
    priority = request.args.get("priority", "")
    if search:
        like = f"%{search}%"
        conds = [Complaint.title.like(like), Complaint.description.like(like),
                 User.name.like(like), User.roll_no.like(like)]
        if search.isdigit():
            conds.append(Complaint.id == int(search))
        q = q.filter(or_(*conds))
    if status in STATUSES:
        q = q.filter(Complaint.status == status)
    if category in CATEGORIES:
        q = q.filter(Complaint.category == category)
    if priority in PRIORITIES:
        q = q.filter(Complaint.priority == priority)
    return q.order_by(Complaint.created_at.desc())


@app.route("/admin/complaints")
@admin_required
def admin_complaints():
    return render_template("admin_complaints.html", complaints=filtered_query().all(),
                           f=request.args)


@app.route("/admin/complaints/<int:cid>/update", methods=["POST"])
@admin_required
def update_complaint(cid):
    c = db.get_or_404(Complaint, cid)
    status = request.form["status"]
    remarks = request.form.get("remarks", "").strip()
    if status not in STATUSES:
        abort(400)
    c.status = status
    c.admin_remarks = remarks or c.admin_remarks
    db.session.add(StatusHistory(complaint_id=c.id, status=status,
                                 remarks=remarks or f"Status changed to {status}"))
    db.session.commit()
    flash(f"Complaint #{c.id} updated to {status}.", "success")
    return redirect(request.referrer or url_for("admin_complaints"))


@app.route("/admin/complaints/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_complaint(cid):
    c = db.get_or_404(Complaint, cid)
    StatusHistory.query.filter_by(complaint_id=c.id).delete()
    db.session.delete(c)
    db.session.commit()
    flash(f"Complaint #{cid} deleted.", "info")
    return redirect(url_for("admin_complaints"))


@app.route("/admin/alerts", methods=["GET", "POST"])
@admin_required
def admin_alerts():
    if request.method == "POST":
        title = request.form["title"].strip()
        msg = request.form["message"].strip()
        if title and msg:
            db.session.add(Alert(title=title, message=msg))
            db.session.commit()
            flash("Alert published.", "success")
        return redirect(url_for("admin_alerts"))
    items = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template("admin_alerts.html", alerts=items)


@app.route("/admin/alerts/<int:aid>/delete", methods=["POST"])
@admin_required
def delete_alert(aid):
    db.session.delete(db.get_or_404(Alert, aid))
    db.session.commit()
    return redirect(url_for("admin_alerts"))


@app.route("/admin/students")
@admin_required
def admin_students():
    students = User.query.filter_by(role="student").order_by(User.created_at.desc()).all()
    return render_template("admin_students.html", students=students)


@app.route("/admin/report.csv")
@admin_required
def report_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Student", "Roll No", "Department", "Category", "Priority",
                "Title", "Status", "Submitted", "Last Updated", "Remarks"])
    for c in filtered_query().all():
        w.writerow([c.id, c.student.name, c.student.roll_no, c.student.department,
                    c.category, c.priority, c.title, c.status,
                    c.created_at.strftime("%Y-%m-%d %H:%M"),
                    c.updated_at.strftime("%Y-%m-%d %H:%M"), c.admin_remarks or ""])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=complaint_report.csv"})


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, msg="You don't have access to this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, msg="Page not found."), 404


with app.app_context():
    db.create_all()
    seed_admin()

if __name__ == "__main__":
    app.run(debug=True)
