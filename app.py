import csv
import io
import secrets
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, Response, abort, stream_with_context)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import or_, func
from sqlalchemy.orm import contains_eager, joinedload

from config import Config
from models import (db, User, Complaint, StatusHistory, Alert,
                    CATEGORIES, PRIORITIES, STATUSES)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ---------- login rate limiting (counts FAILED attempts only, per IP) ----------
# Behind a proxy every visitor can look like one IP; configure ProxyFix before deploying.
limiter = Limiter(get_remote_address, app=app, storage_uri=Config.RATE_LIMIT_STORAGE_URI)
STUDENT_LIMIT = (
    f"{Config.STUDENT_LOGIN_MAX_ATTEMPTS} per {Config.LOGIN_LIMIT_WINDOW_MINUTES} minutes"
)
ADMIN_LIMIT = f"{Config.ADMIN_LOGIN_MAX_ATTEMPTS} per {Config.LOGIN_LIMIT_WINDOW_MINUTES} minutes"
failed_login = lambda resp: resp.status_code == 200  # a failed login re-renders the form (200); success redirects (302)

# ---------- CSRF protection ----------
def get_page():
    """Page number from the URL, clamped so huge values can't crash the database query."""
    return max(1, min(request.args.get("page", 1, type=int), Config.MAX_PAGE))


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.before_request
def csrf_protect():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            abort(400)


# ---------- helpers ----------
def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


CSP = (
    "default-src 'self'; "
    f"script-src 'self' {' '.join(Config.SCRIPT_CDN_ORIGINS)} 'unsafe-inline'; "
    f"style-src 'self' {' '.join(Config.STYLE_CDN_ORIGINS)} 'unsafe-inline'; "
    f"font-src 'self' {' '.join(Config.FONT_CDN_ORIGINS)}; "
    "img-src 'self' data:; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


@app.after_request
def security_headers(resp):
    h = resp.headers
    h.setdefault("Content-Security-Policy", CSP)
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if app.config["SESSION_COOKIE_SECURE"]:  # only meaningful over HTTPS
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if session.get("user_id"):  # private pages must not be cached
        h["Cache-Control"] = "no-store"
    return resp


@app.context_processor
def inject_globals():
    return dict(current_user=current_user(), csrf_token=csrf_token, STATUSES=STATUSES,
                CATEGORIES=CATEGORIES, PRIORITIES=PRIORITIES, asset_urls=Config.ASSET_URLS)


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


COMMON_PASSWORDS = {"password", "password1", "password123", "12345678", "123456789", "qwerty123",
                    "qwertyuiop", "iloveyou", "11111111", "abcd1234", "admin123", "college123"}


def weak_password(pw, email):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if pw.lower() in COMMON_PASSWORDS or pw.isdigit() or len(set(pw)) < 4:
        return "That password is too easy to guess. Mix letters and numbers."
    local = email.split("@")[0]
    if len(local) >= 3 and local in pw.lower():
        return "Password must not contain your email name."
    return None


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
        problem = weak_password(pw, email) if email else None
        if not name or not email:
            flash("Please fill in your name and email.", "danger")
        elif problem:
            flash(problem, "danger")
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
@limiter.limit(STUDENT_LIMIT, methods=["POST"], deduct_when=failed_login)
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
@limiter.limit(ADMIN_LIMIT, methods=["POST"], deduct_when=failed_login)
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
    recent = (Complaint.query.options(joinedload(Complaint.student))
              .order_by(Complaint.created_at.desc()).limit(5).all())
    stats = {
        "total": sum(counts.values()),
        "pending": counts.get("Pending", 0),
        "progress": counts.get("In Progress", 0),
        "resolved": counts.get("Resolved", 0),
        "students": User.query.filter_by(role="student").count(),
    }
    return render_template("admin_dashboard.html", stats=stats, by_cat=by_cat, recent=recent)


def filtered_query():
    q = Complaint.query.join(User).options(contains_eager(Complaint.student))
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
    page = get_page()
    p = filtered_query().paginate(page=page, per_page=app.config["PER_PAGE"], error_out=False)
    return render_template("admin_complaints.html", complaints=p.items, p=p, f=request.args)


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
    page = get_page()
    p = db.paginate(db.select(User).where(User.role == "student").order_by(User.created_at.desc()),
                    page=page, per_page=app.config["PER_PAGE"], error_out=False)
    ids = [u.id for u in p.items]
    counts = {}
    if ids:  # one grouped query for the whole page instead of one query per student
        counts = dict(db.session.query(Complaint.user_id, func.count(Complaint.id))
                      .filter(Complaint.user_id.in_(ids)).group_by(Complaint.user_id).all())
    return render_template("admin_students.html", p=p, counts=counts)


def safe_cell(v):
    """Stop spreadsheet formula injection (=, +, -, @ at the start of a cell)."""
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v


@app.route("/admin/report.csv")
@admin_required
def report_csv():
    def generate():
        buf = io.StringIO()
        w = csv.writer(buf)

        def flush():
            data = buf.getvalue()
            buf.seek(0)
            buf.truncate(0)
            return data

        w.writerow(["ID", "Student", "Roll No", "Department", "Category", "Priority",
                    "Title", "Status", "Submitted", "Last Updated", "Remarks"])
        yield flush()
        for c in filtered_query().yield_per(Config.CSV_BATCH_SIZE):
            w.writerow([c.id, safe_cell(c.student.name), safe_cell(c.student.roll_no),
                        safe_cell(c.student.department), c.category, c.priority,
                        safe_cell(c.title), c.status,
                        c.created_at.strftime("%Y-%m-%d %H:%M"),
                        c.updated_at.strftime("%Y-%m-%d %H:%M"), safe_cell(c.admin_remarks)])
            yield flush()

    return Response(stream_with_context(generate()), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=complaint_report.csv"})


@app.errorhandler(429)
def too_many(_):
    return render_template("error.html", code=429,
                           msg=f"Too many failed login attempts. Wait "
                               f"{Config.LOGIN_LIMIT_WINDOW_MINUTES} minutes and try again."), 429


@app.errorhandler(400)
def bad_request(_):
    return render_template("error.html", code=400,
                           msg="Your session expired or the form was invalid. Go back, reload the page and try again."), 400


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
    app.run(debug=Config.DEBUG)