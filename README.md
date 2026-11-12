# College Complaint & Issue Reporting System

Flask + SQLAlchemy + MySQL + Bootstrap web app (per project synopsis).

## Setup
1. `python -m venv venv && venv\Scripts\activate` (Windows) or `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. In MySQL Workbench: `CREATE DATABASE complaint_db;`
4. Edit the DB user/password in `config.py` (or set `DATABASE_URL`).
   Quick test without MySQL: `set DATABASE_URL=sqlite:///complaints.db`
5. `python app.py` -> http://127.0.0.1:5000

Tables are auto-created on first run. Default admin: `admin@college.edu` / `admin123`
(change via `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars before first run).

## Features
- Student: register, login, submit complaint, track status + history, view alerts
- Admin: dashboard stats, search/filter, update status (Pending / In Progress / Resolved) with remarks, delete, publish alerts, view students, export CSV report
