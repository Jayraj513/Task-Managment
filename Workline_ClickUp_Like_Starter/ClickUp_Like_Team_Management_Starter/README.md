# Workline — Team Task & Project Management Starter

A research-backed starter pack for building an original ClickUp-inspired internal team work management app. This is **not** a clone of ClickUp and does not contain a finished application; it gives Antigravity a clear brief, implementation plan, schema, and test checklist.

## Product goal
Help a manager assign and track team tasks, let team members update their work, and show meaningful project/team dashboards. Start locally with SQLite for a manager demo. If approved for shared team use, switch to PostgreSQL and deploy the web app on Vercel only after verifying the chosen Django deployment adapter and persistent database setup.

## Suggested stack
- Backend: Python 3.12 + Django 5.x (use a compatible stable version)
- UI: Django templates + HTML + Tailwind CSS + vanilla JavaScript
- Charts: Chart.js
- Gantt: Frappe Gantt or another maintained library, after checking license and integration
- Local database: SQLite
- Shared/prod database: PostgreSQL via `DATABASE_URL`
- Auth: Django auth, login/logout, role-based access
- Config: environment variables; never commit secrets

## Quick start (Antigravity should implement these after reading MASTER_PROMPT.md)
1. Create a virtual environment.
2. Install requirements.
3. Run migrations.
4. Create a superuser.
5. Load demo data using a management command.
6. Run the dev server.

Exact commands should be written by Antigravity after generating the app files.

## Important deployment note
SQLite is good for local demo/prototype use, but a local SQLite file is not an appropriate shared production database for a multi-user hosted app. Vercel functions/filesystems can be ephemeral; use managed PostgreSQL for team use and verify Django's deployment/runtime approach. Do not claim production readiness until auth, permissions, migrations, backups, static assets, and smoke tests pass.

## Core navigation
Overview · My Tasks · Projects · Board · List · Calendar · Gantt · Team Workload · Reports · Notifications · Admin

## Build principle
Deliver a polished, working MVP before adding extras. Every visible button must work. Do not fake charts with hard-coded values; all dashboard figures must come from the database and filters must update results.
