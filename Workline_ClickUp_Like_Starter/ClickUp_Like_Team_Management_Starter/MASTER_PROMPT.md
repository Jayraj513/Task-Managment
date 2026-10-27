# ANTIGRAVITY MASTER PROMPT — Workline Team Management

You are a senior full-stack engineer, product designer, QA engineer, and pragmatic technical lead. Build **Workline**, an original ClickUp-inspired internal task and project management web application. Do not copy ClickUp's branding or proprietary design. First inspect every file in this starter folder, especially `PROJECT_BRIEF.md`, `RESEARCH_NOTES.md`, `DATABASE_DESIGN.md`, `IMPLEMENTATION_PLAN.md`, and `ACCEPTANCE_TESTS.md`. Then implement the application in the current workspace.

## Critical delivery rules
1. Start with a brief architecture plan and file tree, then build the working MVP incrementally.
2. Do not stop after making mockups. All core actions must persist to the database.
3. Every button, filter, chart, view toggle and form shown in the UI must work. Remove any nonfunctional controls.
4. Do not use hard-coded dashboard metrics. Derive them from database queries and current filters.
5. Keep code readable, modular, secure, and suitable for a team pilot.
6. Do not ask the user questions unless genuinely blocked; make sensible defaults and document them.
7. Keep SQLite as the default local development database. Configure database selection using environment variables so manager approval can switch the app to PostgreSQL without rewriting models.
8. Do not treat SQLite on Vercel as production storage. For a shared team rollout, use managed PostgreSQL and validate Vercel's current Django runtime/adapter constraints. If reliable deployment is not feasible, explain the blocker and provide the most reliable compatible Python hosting alternative rather than pretending it works.
9. Never expose secrets. Provide `.env.example`, ignore `.env`, and document environment setup.
10. Do not claim completion until migrations, tests, and core user flows have been run.

## Stack
- Python 3.12
- Django (choose a currently supported compatible version)
- Django templates, HTML, Tailwind CSS, vanilla JavaScript
- Chart.js for analytics
- SQLite locally; PostgreSQL in shared deployment
- `dj-database-url` or equivalent for `DATABASE_URL`
- `psycopg` for PostgreSQL
- Use maintained, license-checked libraries for Gantt/calendar functionality
- Production static files configured with an appropriate Django static-file solution compatible with the chosen host

## Design direction
Create a distinctive, polished, professional workspace UI:
- Dark navy/charcoal sidebar, light neutral canvas, one restrained accent color, clean typography.
- Left sidebar: Overview, My Tasks, Projects, Board, List, Calendar, Gantt, Team Workload, Reports, Notifications, Settings.
- Top bar: breadcrumbs, global search, quick-create, notification icon, user menu.
- Responsive for desktop first, usable on tablet/mobile.
- Use compact cards, thoughtful whitespace, clear status chips, priority indicators, empty states and loading feedback.
- Avoid copying ClickUp's exact colors, logo, text, or screen layout.
- Include a “Workline” wordmark as plain text unless an original logo is designed.
- Ensure keyboard focus, labels, contrast and accessible controls.

## User roles and permissions
Implement at least:
- Admin: all workspace settings, users, projects, tasks, reports.
- Manager: create/manage assigned projects and team tasks, view team dashboards.
- Member: view projects they belong to; update assigned tasks; comment and log time; do not manage users or change workspace settings.
- Viewer: read-only access to explicitly shared projects and dashboards.

Enforce permissions on the server, not just by hiding UI elements. Use Django authentication and groups/permissions or a clean custom role model. Add tests for permission boundaries.

## Core models
Implement models based on `DATABASE_DESIGN.md`. Include created/updated timestamps, indexes for common filters, useful `__str__` methods, validation, and sensible delete behavior. Prefer normalized relational fields over comma-separated text. Add migrations.

## MVP pages and behavior
1. Login/logout and role-aware navigation.
2. Overview dashboard:
   - total open, completed this week, overdue, blocked/unassigned tasks
   - task distribution by status and priority
   - tasks by assignee
   - completion trend over time
   - recently updated tasks
   - filters by project, assignee, status, and date range
   - click a chart segment/card to open a filtered task list where practical
3. My Tasks:
   - assigned to current user; filters by due date, status, priority
   - “Today”, “Upcoming”, “Overdue”, “Completed” groupings
4. Projects:
   - project list, create/edit/archive, owner, dates, status, progress
   - project detail with summary, members, milestones, tasks, recent activity
5. Task management:
   - create/read/update/archive tasks
   - title, description, project, assignee, reporter, status, priority, start date, due date, estimate, progress, tags, parent task, blocked reason
   - task detail page/drawer with comments, activity history, subtasks, dependencies and attachments
   - validate due date is not before start date
   - use soft archive where useful
6. Board:
   - Kanban columns from task statuses; drag/drop status change with server persistence and permission validation
7. List/Table:
   - sortable columns, filters, pagination, inline status/priority updates if safe
8. Calendar:
   - task due dates in month/week view; click date/task to create/open task
9. Gantt:
   - task bars from start/due dates, milestones, dependency links, day/week/month zoom
   - if drag-to-reschedule is implemented, save changes server-side and show clear feedback
   - avoid fake dependency lines; model and validate dependencies
10. Team Workload:
   - tasks and estimated hours by assignee and week; flag overload using a documented configurable capacity
11. Reports:
   - overdue tasks, completion rate/trend, completed tasks by member, work by status/priority, unassigned work, estimate vs logged time
   - CSV export for filtered reports
12. Notifications:
   - in-app notification for assignment, mention/comment, due date approaching, status change where appropriate
13. Admin:
   - manage users/roles, projects, statuses and demo data
14. Activity log:
   - record meaningful create/update/status/assignment/comment events with actor and timestamp.

## Analytics definitions
Document KPI definitions in code/docs. Make all metrics query-backed. Handle timezone and date ranges correctly. Avoid division-by-zero. Exclude archived/cancelled tasks where appropriate and state exclusions in UI/help text.

## Seed data
Create a management command, e.g. `python manage.py seed_demo`, that creates:
- one demo workspace/team
- admin/manager/member/viewer demo accounts (passwords must be clearly marked demo-only and must be changed)
- 3 projects
- at least 25 realistic tasks across statuses/priorities/assignees/dates
- comments, milestones, dependencies and time entries if models exist
Ensure repeat runs are idempotent and never overwrite real users/passwords unexpectedly.

## Security and reliability
- CSRF protection, secure form handling, ORM queries (no raw SQL unless justified)
- Server-side permission checks for every mutation
- File upload type/size validation and safe storage path; never execute uploads
- Pagination and query validation
- environment-based `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, database URL
- production HTTPS/security settings behind environment flags
- clear 403/404/500 pages
- database migrations and documented backup/restore process
- avoid storing secrets in git; add `.gitignore`
- add tests for auth, CRUD, filters, KPI calculations and permissions

## Database switch requirement
Create a single database configuration path:
- no `DATABASE_URL` => SQLite at `BASE_DIR / "db.sqlite3"`
- `DATABASE_URL` beginning with `postgres://` or `postgresql://` => PostgreSQL config using a supported parser/driver
- keep models/migrations portable
- document `pip install` and environment variables for PostgreSQL
- do not require a developer to edit model files when switching database
- provide a migration checklist for SQLite demo -> PostgreSQL pilot; explain that production data migration needs a deliberate export/import or migration process, not merely changing the URL

## Vercel/deployment
Inspect current Vercel Django/Python deployment requirements before generating deployment files. Do not invent a working `vercel.json` based on outdated examples. Add deployment config only if it is compatible with current platform guidance and testable. Production database must be external managed PostgreSQL. Document required environment variables and migration/collectstatic commands. If Vercel cannot reliably run the selected Django app, clearly state that and recommend a compatible host for the Django backend. Never imply SQLite's local file will persist on Vercel.

## Required output
- Working application and migrations
- `README.md` with exact Windows PowerShell commands and deployment instructions
- `.env.example`, `.gitignore`, requirements file
- database models and seed command
- automated tests and test report
- `IMPLEMENTATION_STATUS.md` listing complete/partial/not implemented features honestly
- screenshot or walkthrough notes if supported
- final summary: what works, how to run, demo credentials, tests run, known limitations, deployment blockers

## Suggested build sequence
Phase 1: project scaffold, settings, auth, models, migrations, seed data.
Phase 2: task/project CRUD, permissions, My Tasks, List and Board.
Phase 3: dashboards, Chart.js, filters, reports/CSV.
Phase 4: comments/activity/subtasks/dependencies/time entries.
Phase 5: Calendar, Gantt and workload.
Phase 6: responsive polish, accessibility, tests, docs and deployment review.

Begin by inspecting the starter files and giving a concise plan. Then proceed to implement Phase 1 through Phase 3 at minimum before asking for review. Do not stop at a plan.
