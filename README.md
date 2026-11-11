# College Complaint & Issue Reporting System

A web application where students report college issues online and track them to resolution, and administrators manage every complaint from one dashboard. It replaces paper forms and manual registers with a searchable, central record.

Built with **Python, Flask, SQLAlchemy and MySQL**, with a Bootstrap 5 front end.

<!--
  AUTHOR NOTE (delete this block before submitting):
  1. Create the folder  docs/screenshots/  in the project root.
  2. Save your screenshots there using the exact file names used below.
  3. GitHub shows them automatically. A missing file shows as a broken image.
-->

![Home page](docs/screenshots/01-home.png)

---

## Table of Contents

1. [Features](#features)
2. [Screenshots](#screenshots)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [Configuration](#configuration)
7. [How to Use](#how-to-use)
8. [Routes](#routes)
9. [Database Design](#database-design)
10. [Security](#security)
11. [Security Testing](#security-testing)
12. [Troubleshooting](#troubleshooting)
13. [Known Limitations and Future Work](#known-limitations-and-future-work)
14. [Project Team](#project-team)

---

## Features

### Students
- Register and log in with a student account (name, roll number, department, email, password).
- Submit a complaint with a title, category, priority (Low, Medium, High) and description.
- Categories: Academic, Hostel, Library, Canteen, Infrastructure, Transport, Faculty, Examination, Other.
- See all of their own complaints and filter them by status.
- Open a complaint to see its full history: every status change with its date and any remark from the administration.
- Read alerts published by the administration.

### Administrator
- Dashboard with totals for all, Pending, In Progress and Resolved complaints, the number of registered students, a breakdown by category, and the five most recent complaints.
- Complaint list with search (title, description, student name, roll number or complaint ID) and filters for status, category and priority. Results are paginated, 20 per page.
- Change a complaint's status (Pending, In Progress, Resolved) and add a remark the student can read.
- Delete complaints.
- Publish and delete alerts shown on the home page and the alerts page.
- View registered students with the number of complaints each has filed.
- Export the currently filtered complaints as a CSV report.

---

## Screenshots

### Public pages

| Home | Alerts |
|---|---|
| ![Home page](docs/screenshots/01-home.png) | ![Alerts page](docs/screenshots/10-alerts.png) |

### Student

| Register | Student login |
|---|---|
| ![Student registration](docs/screenshots/02-register.png) | ![Student login](docs/screenshots/03-student-login.png) |

| Submit a complaint | My complaints |
|---|---|
| ![New complaint form](docs/screenshots/04-new-complaint.png) | ![My complaints list](docs/screenshots/05-my-complaints.png) |

**Complaint detail with status history**

![Complaint detail](docs/screenshots/06-complaint-detail.png)

### Administrator

| Admin login | Dashboard |
|---|---|
| ![Admin login](docs/screenshots/07-admin-login.png) | ![Admin dashboard](docs/screenshots/08-admin-dashboard.png) |

**Complaint management with search and filters**

![Admin complaints](docs/screenshots/09-admin-complaints.png)

| Publish alerts | Registered students |
|---|---|
| ![Publish alerts](docs/screenshots/11-admin-alerts.png) | ![Students list](docs/screenshots/12-admin-students.png) |

### Security test results

![Security tests](docs/screenshots/13-security-tests.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Web framework | Flask |
| Database access | SQLAlchemy through Flask-SQLAlchemy |
| Database | MySQL (SQLite for quick local testing) |
| MySQL driver | PyMySQL |
| Rate limiting | Flask-Limiter |
| Front end | HTML, CSS, Bootstrap 5, JavaScript |
| Tools | Visual Studio Code, MySQL Workbench |

---

## Project Structure

```
Complaint/
├── app.py                 # Routes, access control, CSRF, security headers, rate limiting
├── models.py              # Database tables (User, Complaint, StatusHistory, Alert)
├── config.py              # Settings read from environment variables
├── requirements.txt       # Python dependencies
├── schema.sql             # Reference SQL for MySQL Workbench (the app also creates tables itself)
├── security_tests.py      # Automated security checks
├── README.md
├── docs/
│   └── screenshots/       # Images used in this README
├── static/
│   ├── css/style.css      # Site styling
│   └── js/main.js         # Form validation, flash messages, CSRF token injection
└── templates/
    ├── base.html          # Layout and navigation
    ├── _macros.html       # Status and priority badges
    ├── _pager.html        # Pagination controls
    ├── index.html         # Home page
    ├── register.html, login.html, admin_login.html
    ├── new_complaint.html, my_complaints.html, complaint_detail.html
    ├── alerts.html
    ├── admin_dashboard.html, admin_complaints.html
    ├── admin_alerts.html, admin_students.html
    └── error.html
```

---

## Getting Started

### Requirements

- Python 3.10 or newer
- Git
- MySQL 8 and MySQL Workbench (only if you want to run on MySQL)

### 1. Get the code

```bash
git clone https://github.com/Paras-Gith/Complaint.git
cd Complaint
```

### 2. Create a virtual environment and install packages

Windows (Command Prompt):

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

macOS, Linux and GitHub Codespaces:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Choose a database

**Option A: SQLite (no setup, best for testing)**

```bash
export DATABASE_URL=sqlite:///complaints.db        # Windows CMD: set DATABASE_URL=sqlite:///complaints.db
```

**Option B: MySQL**

1. Open MySQL Workbench, connect to your server and run:
   ```sql
   CREATE DATABASE IF NOT EXISTS complaint_db CHARACTER SET utf8mb4;
   ```
2. Point the app at it:
   ```bash
   export DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost/complaint_db"
   ```

The app creates all tables and the administrator account on first start. You do not need to run `schema.sql`.

> **GitHub Codespaces note:** a Codespace is a remote machine, so its `localhost` is not your laptop. It cannot reach a MySQL server running on your own computer. Use SQLite in a Codespace, or run the project on your own machine to use MySQL.

### 4. Set secrets (recommended even for testing)

```bash
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
export ADMIN_PASSWORD='ChooseAStrongPassword1!'
```

### 5. Run

```bash
python app.py
```

Open http://127.0.0.1:5000. In a Codespace, click **Open in Browser** on the port 5000 popup, or use the **Ports** tab.

---

## Configuration

All settings are read from environment variables. They last only for the terminal session where you set them.

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Database connection string | `mysql+pymysql://root:password@localhost/complaint_db` |
| `SECRET_KEY` | Signs session cookies. Must be long and random in real use | A placeholder (the app prints a warning) |
| `ADMIN_EMAIL` | Email of the administrator created on first run | `admin@college.edu` |
| `ADMIN_PASSWORD` | Password of the administrator created on first run | `admin123` (change it) |
| `FLASK_DEBUG` | Set to `1` for debug mode. Never use online | off |
| `COOKIE_SECURE` | Set to `1` when serving over HTTPS | off |

The administrator account is created only if no admin exists yet. Changing `ADMIN_PASSWORD` later does not change an existing admin. To change it, run:

```bash
python - <<'EOF'
from app import app
from models import db, User
with app.app_context():
    a = User.query.filter_by(role="admin").first()
    a.set_password("YourNewStrongPassword1!")
    db.session.commit()
EOF
```

---

## How to Use

### As a student

1. Open the site and click **Student Register**. Passwords need at least 8 characters, must not be a common password, and must not contain your email name.
2. Log in at `/login`.
3. Choose **New Complaint**, fill in the form and submit.
4. Open **My Complaints** to follow the status. Click a complaint to read the history and the administration's remarks.

### As the administrator

1. Log in at `/admin/login` with the admin email and password.
2. Use **Dashboard** for an overview and **Complaints** to search and filter.
3. Change a complaint's status, add a remark, or delete it.
4. Use **Publish Alerts** for announcements and **Students** to see registered students.
5. Use **Export CSV Report** on the complaints page to download the current filtered list.

Students and the administrator have separate login pages. Each page only accepts accounts of its own role.

---

## Routes

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Home page and latest alerts |
| `/register` | Public | Student registration |
| `/login` | Public | Student login |
| `/admin/login` | Public | Administrator login |
| `/logout` | Logged in | End the session |
| `/alerts` | Public | All alerts |
| `/complaints/new` | Student | Submit a complaint |
| `/my-complaints` | Logged in | Own complaints, with status filter |
| `/complaints/<id>` | Owner or admin | Complaint detail and history |
| `/admin` | Admin | Dashboard |
| `/admin/complaints` | Admin | Search, filter, paginate |
| `/admin/complaints/<id>/update` | Admin (POST) | Change status and add a remark |
| `/admin/complaints/<id>/delete` | Admin (POST) | Delete a complaint |
| `/admin/alerts` | Admin | Publish alerts |
| `/admin/alerts/<id>/delete` | Admin (POST) | Delete an alert |
| `/admin/students` | Admin | Registered students |
| `/admin/report.csv` | Admin | CSV export of the filtered complaints |

---

## Database Design

| Table | Main columns |
|---|---|
| `users` | id, name, email (unique), roll_no, department, password_hash, role (`student` or `admin`), created_at |
| `complaints` | id, user_id, title, category, priority, description, status, admin_remarks, created_at, updated_at |
| `status_history` | id, complaint_id, status, remarks, changed_at |
| `alerts` | id, title, message, created_at |

- One user has many complaints. One complaint has many status history rows, which are deleted with it.
- `status`, `category`, `created_at` and the foreign keys are indexed for faster filtering.
- Indexes are created when the tables are created. If you upgrade an existing database, delete it (SQLite) or add the indexes by hand (MySQL).

---

## Security

- **Passwords** are stored as salted hashes, never as plain text.
- **SQL injection:** all queries go through SQLAlchemy with bound parameters.
- **XSS:** Jinja auto-escaping is on everywhere, and no template uses `|safe`.
- **CSRF:** every POST form carries a per-session token, checked on the server.
- **Access control:** every admin route requires the admin role. Students can read only their own complaints.
- **Login rate limiting:** failed logins are limited per IP address, 10 per 15 minutes for students and 5 per 15 minutes for the admin page.
- **Password policy:** minimum 8 characters, no common passwords, no email name inside the password.
- **Security headers:** Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy and Permissions-Policy. Logged-in pages are sent with `Cache-Control: no-store`.
- **Session cookies** are HttpOnly and SameSite=Lax, and Secure when `COOKIE_SECURE=1`.
- **CSV export** neutralises spreadsheet formulas (cells starting with `=`, `+`, `-` or `@`).
- **Role separation:** a student account cannot log in on the admin page and the reverse.

---

## Security Testing

`security_tests.py` is an automated check that runs against a temporary database, so it never touches real data. It covers SQL injection, command injection, stored and reflected XSS, password hashing, session handling, login throttling, access control (including access to other students' complaints), CSRF, and security headers.

```bash
python security_tests.py
```

Run it only against your own local copy of the project. Each line is reported as PASS, WARN or FAIL, and the script exits with an error code if anything fails. Set a real `SECRET_KEY` and `ADMIN_PASSWORD` first, or those two checks fail on purpose.

For further manual testing, tools such as OWASP ZAP, sqlmap, Bandit and pip-audit are a good next step. Never run them against a server you do not own or have written permission to test.

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Can't connect to MySQL server ... Connection refused` | No MySQL server is reachable. Set `DATABASE_URL=sqlite:///complaints.db`, or start MySQL. |
| `BuildError: Could not build url for endpoint 'logout'` | The `logout` route is missing from `app.py`. Restore it. |
| "Your session expired or the form was invalid" | The CSRF token is missing. Check the `csrf-token` meta tag in `base.html` and the token code at the end of `static/js/main.js`. |
| "Too many failed login attempts" | The login limit was reached. Wait 15 minutes or restart the server (counters are in memory). |
| Admin login fails after changing `ADMIN_PASSWORD` | The admin already existed. Reset the password with the snippet in [Configuration](#configuration). |
| `ModuleNotFoundError` | Activate the virtual environment and run `pip install -r requirements.txt`. |
| `$env:...` or `set ...` does not work | Use the command for your shell. `export` is for bash, `set` for Windows CMD, `$env:` for PowerShell. |
| Page looks unstyled after a CSS change | Hard-refresh with `Ctrl+Shift+R`. |

---

## Known Limitations and Future Work

- Session cookies are stateless, so a copied cookie stays valid until it expires, even after logout. Server-side sessions would fix this.
- Rate limit counters are kept in memory. Use Redis for several workers or a real deployment, and configure the proxy IP setting when running behind a proxy.
- The Content-Security-Policy still allows inline scripts because some templates use inline event handlers.
- No email verification, password reset or email notifications yet.
- Complaints cannot have file attachments yet.
- A JSON REST API would let other systems, such as the main college website or a mobile app, send and read complaints.
- Before going live: use HTTPS, run with a production server such as Gunicorn, use a strong `SECRET_KEY`, change the admin password and set `COOKIE_SECURE=1`.

---

## Project Team

| Name | Role |
|---|---|
| _Your name_ | _Role_ |
| _Team member_ | _Role_ |

**College / Department:** _Uttarakhand Technical University, Department of Computer Science_
**Guide / Submitted to:** _Name_
