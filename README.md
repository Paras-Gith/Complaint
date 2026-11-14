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
Install the local commit hooks with `pre-commit install`. Install Gitleaks as a local
executable as well; the hook scans staged changes before each commit. CI scans full Git
history for secrets.

Run the syntax, lint, formatter, incremental type-check, and security checks:

```sh
python -m compileall -q app.py config.py models.py security_tests.py complaint_app
ruff check --select E4,E7,E9,F,I app.py security_tests.py complaint_app
ruff format --check app.py complaint_app
python -m mypy --follow-imports=skip \
  --disable-error-code=misc --disable-error-code=no-any-return \
  --disable-error-code=untyped-decorator --disable-error-code=union-attr \
  app.py complaint_app
python security_tests.py
```

CI additionally runs `pip-audit -r requirements-dev.txt` and Gitleaks. Mypy is currently an
incremental gate: the legacy SQLAlchemy models and Flask integration produce existing dynamic
typing noise, so those framework-related error codes are excluded while application helper and
route logic is checked. Remove these exclusions as the remaining model/framework typing is
addressed.

In GitHub repository settings, protect `main`: require pull requests, require the `quality`,
`dependency-audit`, and `secret-scan` checks, require branches to be up to date, and block
force pushes and branch deletion.
