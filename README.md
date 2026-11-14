# College Complaint & Issue Reporting System

A Flask application for college students to report and track complaints, and for administrators to manage reports, publish alerts, and review activity. It uses SQLAlchemy with SQLite by default and supports MySQL.

## Features

- Register as a student, sign in, and track complaint status and history.
- Submit complaints with a category and priority.
- Search and filter complaints from the administrator dashboard.
- Update complaint status with remarks, and delete complaints.
- Publish and browse system alerts.
- Review registered students and their complaint counts.
- Export filtered complaints as a streamed CSV report.
- Protect form submissions with CSRF checks, rate-limit failed login attempts, and apply security headers.

## Requirements

- Python 3.12 recommended (the project uses Flask 3.1).
- Windows PowerShell examples below; use the equivalent `python` and `export` commands on macOS/Linux.
- SQLite is used by default. MySQL is optional.

## Install

Open PowerShell in the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Set the required environment variables in the same PowerShell window:

```powershell
$env:SECRET_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))")
$env:ADMIN_EMAIL = "admin@college.edu"
$env:ADMIN_PASSWORD = Read-Host "Enter an initial admin password (at least 16 characters)"
```

Keep the generated `SECRET_KEY` private and stable between app restarts. These environment variables apply only to the current terminal session; configure persistent environment variables or a secret manager for longer-term use. The initial admin account is created only when the database has no admin user. Changing `ADMIN_PASSWORD` later does not reset an existing account's password.

### Optional MySQL configuration

The default database is `instance/complaints.db`. To use MySQL, create a database named `complaint_db`, then set `DATABASE_URL` before starting the app:

```powershell
$env:DATABASE_URL = "mysql+pymysql://DB_USER:DB_PASSWORD@localhost/complaint_db"
```

Keep database credentials out of source control. The optional schema setup script is [schema.sql](schema.sql).

## Run

In the same terminal where the environment variables are set:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Stop the development server with **Ctrl+C**.

For macOS/Linux, activate the virtual environment and set equivalent variables:

```sh
source .venv/bin/activate
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ADMIN_EMAIL="admin@college.edu"
export ADMIN_PASSWORD="choose-a-unique-password-at-least-16-characters"
python app.py
```

## Tests

Run the security and behavior regression checks from the project root:

```powershell
.\.venv\Scripts\python.exe security_tests.py
```

The script uses a temporary SQLite database and does not use the application's normal database.

## Lint, format, and type-check

Development tools are listed in `requirements-dev.txt`; settings are in `pyproject.toml`.
Install the local Git hooks after installing requirements:

```powershell
.\.venv\Scripts\pre-commit.exe install
```

Gitleaks must also be installed as a local executable for the staged-secret hook. Run all hooks manually with:

```powershell
.\.venv\Scripts\pre-commit.exe run --all-files
```

Run the CI quality checks individually:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py config.py models.py security_tests.py complaint_app
.\.venv\Scripts\ruff.exe check --select E4,E7,E9,F,I app.py security_tests.py complaint_app
.\.venv\Scripts\ruff.exe format --check app.py complaint_app
.\.venv\Scripts\python.exe -m mypy --follow-imports=skip `
  --disable-error-code=misc --disable-error-code=no-any-return `
  --disable-error-code=untyped-decorator --disable-error-code=union-attr `
  app.py complaint_app
.\.venv\Scripts\python.exe security_tests.py
.\.venv\Scripts\pip-audit.exe -r requirements-dev.txt
```

Mypy is an incremental gate: dynamic SQLAlchemy model and Flask integration typing currently produces legacy noise, so selected framework-related diagnostics are excluded. Tighten those exclusions as model and framework typing improves.

## Local hooks and CI quality gates

The pre-commit hooks check Python lint and formatting, run the incremental mypy gate, and scan staged changes for secrets with Gitleaks. GitHub Actions runs the quality and security regression checks, audits runtime and development dependencies with `pip-audit`, and scans repository history for secrets on pull requests, pushes to `main`, and a weekly schedule.

In GitHub repository settings, protect `main`: require pull requests and require the **quality**, **dependency-audit**, and **secret-scan** status checks before merging. Also require branches to be up to date and block force pushes and branch deletion.

## Screenshots

Save screenshots in a `screenshots/` folder at the project root using the filenames below. The image links are placeholders until you add the matching files.

### Home page

![Home page screenshot placeholder](screenshots/home.png)

### Student complaint form

![New complaint form screenshot placeholder](screenshots/new-complaint.png)

### Student complaint tracking

![My complaints screenshot placeholder](screenshots/my-complaints.png)

### Admin dashboard

![Admin dashboard screenshot placeholder](screenshots/admin-dashboard.png)

### Admin complaint management

![Admin complaints screenshot placeholder](screenshots/admin-complaints.png)

## How the project works

```mermaid
flowchart TD
    Browser[Student or admin browser]
    Entry[app.py<br/>WSGI and development entry point]
    Factory[complaint_app/application.py<br/>Flask app factory]
    Routes[complaint_app/routes<br/>Public, auth, student, admin routes]
    Security[complaint_app/security.py<br/>CSRF, auth guards, headers]
    Services[complaint_app/services.py<br/>Business rules and shared queries]
    Pagination[complaint_app/pagination.py<br/>Bounded page parsing]
    Models[models.py<br/>SQLAlchemy models]
    Config[config.py<br/>Environment-backed settings]
    Database[(SQLite by default<br/>MySQL optional)]
    Templates[templates<br/>Jinja pages]
    Static[static<br/>CSS and JavaScript]

    Browser -->|HTTP request| Entry
    Entry --> Factory
    Factory --> Routes
    Factory --> Security
    Factory --> Config
    Routes --> Services
    Routes --> Pagination
    Routes --> Models
    Services --> Models
    Models --> Database
    Routes -->|render response| Templates
    Templates --> Static
    Templates -->|HTML| Browser
```

### File responsibilities

- `app.py` creates the Flask app and exposes `app` and `db` for WSGI servers and compatibility.
- `complaint_app/application.py` configures the app, initializes extensions, registers routes and error handlers, and creates database tables.
- `complaint_app/routes/public.py`, `auth.py`, `student.py`, and `admin.py` define endpoint behavior by feature area.
- `complaint_app/security.py` provides CSRF protection, session-based user lookup, authorization decorators, response headers, and template context.
- `complaint_app/services.py` contains password checks, admin seeding, and shared complaint query logic.
- `complaint_app/pagination.py` clamps user-provided page numbers.
- `config.py` validates environment settings for secrets, database, cookies, rate limits, pagination, and external asset URLs.
- `models.py` defines users, complaints, status history, alerts, and the SQLAlchemy database extension.
- `schema.sql` provides an optional MySQL schema script; tables are also created by the app.
- `templates/` contains the student, public, and administrator Jinja pages and shared template fragments.
- `static/css/style.css` and `static/js/main.js` provide frontend styling and JavaScript.
- `security_tests.py` exercises security controls and core application behavior using a temporary database.
- `.pre-commit-config.yaml` defines local commit hooks; `.github/workflows/ci.yml` defines automated CI.
- `requirements.txt` lists runtime dependencies; `requirements-dev.txt` adds development and audit tools.

## Project layout

```text
.
├── app.py
├── config.py
├── models.py
├── schema.sql
├── security_tests.py
├── complaint_app/
│   ├── application.py
│   ├── pagination.py
│   ├── security.py
│   ├── services.py
│   └── routes/
│       ├── __init__.py
│       ├── admin.py
│       ├── auth.py
│       ├── public.py
│       └── student.py
├── templates/
├── static/
├── instance/
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```
