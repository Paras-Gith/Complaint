# College Complaint & Issue Reporting System

Flask + SQLAlchemy + MySQL + Bootstrap web app.

## Setup
1. `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
2. `python -m pip install -r requirements-dev.txt`
3. Configure the required secrets:

   ```sh
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   export ADMIN_EMAIL="admin@college.edu"
   export ADMIN_PASSWORD="choose-a-unique-password-at-least-16-characters"
   ```

4. The default database is local SQLite. For MySQL, create `complaint_db` and set
   `DATABASE_URL` to your MySQL connection URI. Keep database credentials out of source.
5. Run `python app.py` and open http://127.0.0.1:5000.

Tables and the initial administrator are created on first run. Keep `SECRET_KEY` stable
and private; configure it and the administrator password through a secret manager in
production. Configure Redis via `RATE_LIMIT_STORAGE_URI` when running multiple workers.

## Application structure
- `app.py` is the development/WSGI entry point and re-exports `app` and `db`.
- `complaint_app/application.py` builds and configures the Flask application.
- `complaint_app/security.py` owns request protections, auth decorators, and template context.
- `complaint_app/routes/` separates public, authentication, student, and admin endpoints.
- `complaint_app/services.py` contains shared business rules and complaint queries.
- `complaint_app/pagination.py` centralizes bounded page-number parsing.

Complaint and alert lists are paginated; CSV reports are streamed in bounded batches.

## Code quality checks
Install the development dependencies with `python -m pip install -r requirements-dev.txt`.
Run the syntax, lint, formatter, and type-check baselines and save the complete output:

```sh
{
  status=0
  python -m compileall -q app.py config.py models.py security_tests.py complaint_app
  result=$?; echo "[syntax exit=$result]"; [ "$result" -eq 0 ] || status=1
  python -m ruff check app.py config.py models.py security_tests.py complaint_app
  result=$?; echo "[ruff exit=$result]"; [ "$result" -eq 0 ] || status=1
  python -m ruff format --check app.py config.py models.py security_tests.py complaint_app
  result=$?; echo "[format exit=$result]"; [ "$result" -eq 0 ] || status=1
  python -m mypy
  result=$?; echo "[mypy exit=$result]"; [ "$result" -eq 0 ] || status=1
  exit "$status"
} > baseline-audit.log 2>&1
```

Run the behavioral/security regression suite with `python security_tests.py`.
