"""Security checks for the College Complaint System.

Run from the project folder:   python security_tests.py
It uses a throwaway SQLite database, so your real data is never touched.
Only run this against YOUR OWN local copy of the project.
"""
import glob
import os
import re
import sys
import tempfile
from urllib.parse import urlparse

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/security_test.db"

from app import app, db                      # noqa: E402
from config import Config                    # noqa: E402
from models import User, Complaint           # noqa: E402

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
rows = []
PW = "Sup3r-secret!"
_ip = [0]
P1 = "<script>alert(1)</script>"
P2 = '"><img src=x onerror=alert(1)>'


def check(area, name, ok, detail="", warn=False):
    rows.append((area, PASS if ok else (WARN if warn else FAIL), name, detail))


def post(c, path, **data):
    with c.session_transaction() as s:
        s.setdefault("_csrf", "x" * 32)
        tok = s["_csrf"]
    return c.post(path, data=dict(data, _csrf=tok))


def loc(r):
    return urlparse(r.headers.get("Location", "")).path


def newc():
    """Test client with its own IP, so the login limiter doesn't throttle unrelated tests."""
    _ip[0] += 1
    c = app.test_client()
    c.environ_base["REMOTE_ADDR"] = f"10.0.{_ip[0] // 250}.{_ip[0] % 250 + 1}"
    return c


def student(email, name="Student", pw=PW, **extra):
    c = newc()
    post(c, "/register", name=name, email=email, password=pw, **extra)
    post(c, "/login", email=email, password=pw)
    return c


def admin_client():
    c = newc()
    post(c, "/admin/login", email=Config.ADMIN_EMAIL, password=Config.ADMIN_PASSWORD)
    return c


def src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------- setup data ----------
alice = student("a@t.com", "Alice")
bob = student("b@t.com", "Bob")
evil = student("c@t.com", P1 + P2)
post(alice, "/complaints/new", title="Broken fan", description="Fan is broken in room 12",
     category="Hostel", priority="High")
post(evil, "/complaints/new", title=P1 + P2, description=P2 + P1, category="Hostel", priority="Low")
adm = admin_client()
with app.app_context():
    cid_a = Complaint.query.filter_by(title="Broken fan").first().id
    cid_e = Complaint.query.filter(Complaint.title.like("%script%")).first().id
post(adm, f"/admin/complaints/{cid_e}/update", status="In Progress", remarks=P1 + P2)
post(adm, "/admin/alerts", title=P1 + P2, message=P2 + P1)
check("Setup", "Admin test login works", adm.get("/admin").status_code == 200,
      "If this fails, set ADMIN_EMAIL / ADMIN_PASSWORD env vars to match your admin")

# ---------- 1. INJECTION ----------
A = "Injection"
sqli = ["' OR '1'='1' --", "admin@college.edu' --", '" OR ""="', "' OR 1=1 #"]
ok = True
for path in ("/login", "/admin/login"):
    for p in sqli:
        c = newc()
        r1 = post(c, path, email=p, password="x")
        r2 = post(c, path, email=Config.ADMIN_EMAIL, password=p)
        ok &= r1.status_code == 200 and r2.status_code == 200
check(A, "SQL injection in login forms is rejected", ok)

base = adm.get("/admin/complaints", query_string={"q": "zzz-nothing"}).get_data(as_text=True)
inj = adm.get("/admin/complaints", query_string={"q": "' OR 1=1 --"})
union = adm.get("/admin/complaints",
                query_string={"q": "' UNION SELECT password_hash,2,3 FROM users --"}).get_data(as_text=True)
check(A, "SQL injection in search box is treated as plain text",
      inj.status_code == 200 and "No complaints match" in inj.get_data(as_text=True)
      and "No complaints match" in base and "scrypt:" not in union and "pbkdf2:" not in union)

ok = True
for k in ("status", "category", "priority"):
    ok &= adm.get("/admin/complaints", query_string={k: "' OR 1=1 --"}).status_code == 200
for pg in ("-1", "0", "abc", "999999999999999999999", "1;DROP TABLE users"):
    ok &= adm.get("/admin/complaints", query_string={"page": pg}).status_code == 200
    ok &= adm.get("/admin/students", query_string={"page": pg}).status_code == 200
check(A, "Filter and page parameters survive hostile values (no 500 errors)", ok)

code = "".join(src(f) for f in ("app.py", "models.py", "config.py"))
bad = re.findall(r"\b(os\.system|subprocess|os\.popen|eval\(|exec\(|pickle|yaml\.load|"
                 r"render_template_string|__import__|shell=True)", code)
check(A, "No command execution, eval or unsafe deserialisation in the code", not bad, ", ".join(set(bad)))

tpl = "".join(src(f) for f in glob.glob("templates/*.html"))
check(A, "Templates never disable auto-escaping (|safe, autoescape off, Markup)",
      not re.search(r"\|\s*safe|autoescape\s+false|Markup\(", tpl + code))

pages = ["/", "/admin", "/admin/complaints", "/admin/students", "/admin/alerts", "/alerts",
         f"/complaints/{cid_e}"]
leaks = [p for p in pages if P1 in (b := adm.get(p).get_data(as_text=True)) or P2 in b]
leaks += ["/my-complaints (evil user)"] if P1 in evil.get("/my-complaints").get_data(as_text=True) else []
check(A, "Stored XSS (names, titles, remarks, alerts) is escaped on every page", not leaks, ", ".join(leaks))
refl = adm.get("/admin/complaints", query_string={"q": P2}).get_data(as_text=True)
check(A, "Reflected XSS in search box is escaped", P2 not in refl and P1 not in refl)

# ---------- 2. AUTHENTICATION & SESSIONS ----------
A = "Auth/Session"
with app.app_context():
    u = User.query.filter_by(email="a@t.com").first()
    check(A, "Passwords are stored hashed", u.password_hash.startswith(("scrypt:", "pbkdf2:")))
    role_ok = User.query.filter_by(email="d@t.com").first() is None
c = newc()
post(c, "/register", name="D", email="d@t.com", password=PW, role="admin")
with app.app_context():
    d = User.query.filter_by(email="d@t.com").first()
    check(A, "Registration cannot be used to create an admin (mass assignment)", d and d.role == "student")

m1 = post(newc(), "/login", email="nobody@t.com", password=PW).get_data(as_text=True)
m2 = post(newc(), "/login", email="a@t.com", password="wrong").get_data(as_text=True)
check(A, "Login gives the same error for unknown email and wrong password",
      "Invalid student email or password." in m1 and "Invalid student email or password." in m2)

c = newc()
with c.session_transaction() as s:
    s["pre_login"] = 1
r = post(c, "/login", email="a@t.com", password=PW)
cookies = " ".join(r.headers.getlist("Set-Cookie"))
check(A, "Session cookie has HttpOnly", "HttpOnly" in cookies)
check(A, "Session cookie has SameSite", "SameSite" in cookies)
check(A, "Session cookie has Secure flag", "Secure" in cookies,
      "Off on http://localhost (fine); set COOKIE_SECURE=1 when serving over HTTPS", warn=True)
with c.session_transaction() as s:
    check(A, "Session is reset on login (no session fixation)", "pre_login" not in s)

old = None
try:
    old = c.get_cookie("session").value
except Exception:
    pass
c.get("/logout")
check(A, "Logout ends the browser session", c.get("/my-complaints").status_code == 302)
if old:
    c2 = newc()
    c2.set_cookie("session", old)
    check(A, "A copied session cookie stops working after logout",
          c2.get("/my-complaints").status_code == 302,
          "Flask cookies are stateless: a stolen cookie stays valid until it expires", warn=True)

bf = newc()
codes = [post(bf, "/admin/login", email=Config.ADMIN_EMAIL, password=f"wrong{i}").status_code for i in range(25)]
good = post(bf, "/admin/login", email=Config.ADMIN_EMAIL, password=Config.ADMIN_PASSWORD)
check(A, "Admin login: repeated wrong passwords are throttled",
      429 in codes and good.status_code == 429, "25 wrong attempts, then the correct password still worked")
sc = newc()
scodes = [post(sc, "/login", email="a@t.com", password=f"wrong{i}").status_code for i in range(15)]
check(A, "Student login: repeated wrong passwords are throttled", 429 in scodes,
      "15 wrong attempts were all processed")

check(A, "Default admin password has been changed", Config.ADMIN_PASSWORD != "admin123",
      "Admin password is the public default 'admin123'")
c = newc()
weak = [post(newc(), "/register", name="W", email=f"wendy{i}@t.com", password=p).status_code
        for i, p in enumerate(["123456", "password1", "short1", "xwendy3-pass"])]
check(A, "Weak passwords (too short, common, or containing the email) are refused",
      all(s != 302 for s in weak), "A weak password was accepted")

default_key = app.config["SECRET_KEY"] == "change-this-in-production"
detail = ""
if default_key:
    from flask.sessions import SecureCookieSessionInterface
    with app.app_context():
        aid = User.query.filter_by(role="admin").first().id
    forged = SecureCookieSessionInterface().get_signing_serializer(app).dumps({"user_id": aid})
    fc = newc()
    fc.set_cookie("session", forged)
    detail = "Anyone who knows the default key can forge an admin cookie. Forged cookie accepted: " \
             + str(fc.get("/admin").status_code == 200)
check(A, "SECRET_KEY is not the default value", not default_key, detail)

# ---------- 3. ACCESS CONTROL ----------
A = "Access control"
admin_gets = ["/admin", "/admin/complaints", "/admin/students", "/admin/alerts", "/admin/report.csv"]
anon = newc()
check(A, "Anonymous users are redirected from every protected page",
      all(anon.get(p).status_code == 302 for p in admin_gets + ["/my-complaints", "/complaints/new", f"/complaints/{cid_a}"]))
check(A, "Students get 403 on every admin page", all(bob.get(p).status_code == 403 for p in admin_gets))

writes = [(f"/admin/complaints/{cid_a}/update", dict(status="Resolved", remarks="hacked")),
          (f"/admin/complaints/{cid_a}/delete", {}),
          ("/admin/alerts", dict(title="fake", message="fake")),
          ("/admin/alerts/1/delete", {})]
check(A, "Students cannot change or delete data through admin endpoints",
      all(post(bob, p, **d).status_code == 403 for p, d in writes))
check(A, "Anonymous users cannot call admin write endpoints",
      all(post(anon, p, **d).status_code == 302 for p, d in writes))
with app.app_context():
    cc = db.session.get(Complaint, cid_a)
    check(A, "Data was not changed by those attempts", cc is not None and cc.status == "Pending")

check(A, "Student cannot read another student's complaint (IDOR)", bob.get(f"/complaints/{cid_a}").status_code == 403)
check(A, "Owner and admin can read the complaint",
      alice.get(f"/complaints/{cid_a}").status_code == 200 and adm.get(f"/complaints/{cid_a}").status_code == 200)
check(A, "Admin cannot use the student complaint form", adm.get("/complaints/new").status_code == 403)
check(A, "Delete endpoint refuses GET (no delete by link or image tag)",
      adm.get(f"/admin/complaints/{cid_a}/delete").status_code == 405)
check(A, "POST without CSRF token is rejected",
      adm.post(f"/admin/complaints/{cid_a}/update", data=dict(status="Resolved")).status_code == 400)
check(A, "Templates send the CSRF token (meta tag in base.html)", "csrf-token" in src("templates/base.html"))

# ---------- 4. MISCONFIGURATION & HEADERS ----------
A = "Config/Headers"
h = newc().get("/").headers
need = {"Content-Security-Policy": "CSP", "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "clickjacking protection", "Referrer-Policy": "referrer leakage",
        "Permissions-Policy": "browser feature limits"}
for k, why in need.items():
    check(A, f"Header {k} is set", k in h, why)
check(A, "Header Strict-Transport-Security is set", "Strict-Transport-Security" in h,
      "Only valid over HTTPS; enable with COOKIE_SECURE=1", warn=True)
csp = h.get("Content-Security-Policy", "")
check(A, "CSP does not allow 'unsafe-inline' scripts", csp != "" and "unsafe-inline" not in
      csp.split("style-src")[0], "Inline onclick/onchange handlers in templates need refactoring first", warn=True)
check(A, "Logged-in pages are not cached by the browser",
      "no-store" in alice.get("/my-complaints").headers.get("Cache-Control", ""),
      "Back button after logout can show private pages", warn=True)
check(A, "Debug mode is off", not app.debug and os.environ.get("FLASK_DEBUG") != "1")
nf = newc().get("/does-not-exist")
body = nf.get_data(as_text=True)
check(A, "Error pages do not leak stack traces", nf.status_code == 404 and "Traceback" not in body
      and "werkzeug" not in body.lower())
check(A, "Database URL has no hard-coded root/password default", "root:password" not in src("config.py"),
      "config.py still has a placeholder root password default", warn=True)

# ---------- report ----------
w = max(len(r[2]) for r in rows)
cur = None
for area, status, name, detail in rows:
    if area != cur:
        print(f"\n== {area} ==")
        cur = area
    mark = {"PASS": "[ PASS ]", "FAIL": "[ FAIL ]", "WARN": "[ WARN ]"}[status]
    print(f"{mark} {name}" + (f"\n         -> {detail}" if status != PASS and detail else ""))
n = {s: sum(1 for r in rows if r[1] == s) for s in (PASS, WARN, FAIL)}
print(f"\nSummary: {n[PASS]} passed, {n[WARN]} warnings, {n[FAIL]} failed")
sys.exit(1 if n[FAIL] else 0)