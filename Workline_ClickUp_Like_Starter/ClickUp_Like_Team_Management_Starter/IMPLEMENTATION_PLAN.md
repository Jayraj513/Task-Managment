# Implementation Plan

## Phase 0 — Inspect and plan
- Read this brief and research notes.
- Confirm supported Django/Python versions and current Vercel runtime guidance.
- Select maintained, license-checked Gantt/calendar libraries.

## Phase 1 — Foundation
- Django project and apps: accounts, workspaces, projects, tasks, analytics, notifications.
- Environment settings and SQLite default.
- Auth, role model, permissions.
- Models, migrations, seed command.
- Admin configuration and basic tests.

## Phase 2 — Core workflows
- Project/task CRUD.
- Task details, comments, subtasks, tags, activity.
- My Tasks, List and Kanban Board.
- Search, filters, pagination.

## Phase 3 — Dashboards and reports
- Manager dashboard and individual dashboard.
- Query-backed metrics and Chart.js charts.
- Team workload table.
- CSV export and KPI tests.

## Phase 4 — Planning
- Calendar, Gantt, milestones, dependencies.
- Time entries and estimate-vs-actual reporting.

## Phase 5 — Team pilot hardening
- Notifications, uploads, accessibility, responsive layout.
- Permission/security tests, backup/restore documentation.
- PostgreSQL configuration and staging deployment review.

## Definition of done
- Fresh clone can run on Windows using README commands.
- Migrations and seed command run successfully.
- No critical error in main user journeys.
- Core CRUD and permissions covered by tests.
- Dashboards reflect current database state.
- Honest status report and deployment limitations documented.
