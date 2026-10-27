# Workline — Architecture Plan & Implementation Roadmap

## 1. Overview
**Workline** is a modern, high-performance, ClickUp-inspired work and project management web application built with Python 3.12, Django 5.2, Tailwind CSS, vanilla JavaScript, and Chart.js.

## 2. Architecture & File Structure
```
d:\Task Management/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── IMPLEMENTATION_STATUS.md
├── workline/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── models.py (UserProfile, Role choices: Admin, Manager, Member, Viewer)
│   │   ├── views.py (Login, Logout, Profile, User Admin)
│   │   ├── permissions.py (Role permission decorators & helpers)
│   │   └── urls.py
│   ├── workspaces/
│   │   ├── models.py (Workspace, WorkspaceMembership)
│   │   ├── views.py (Workspace settings, team management)
│   │   └── urls.py
│   ├── projects/
│   │   ├── models.py (Project, ProjectMembership, Milestone)
│   │   ├── views.py (Project List, Detail, Create, Edit, Archive)
│   │   └── urls.py
│   ├── tasks/
│   │   ├── models.py (Task, Tag, TaskDependency, Comment, Attachment, TimeEntry)
│   │   ├── views.py (Task CRUD, Board, List, Calendar, Gantt, Quick Create, Inline Updates)
│   │   ├── services.py (Dependency validation, cyclic graph detection)
│   │   └── urls.py
│   ├── analytics/
│   │   ├── views.py (Overview Dashboard, Reports, Team Workload, CSV Export)
│   │   ├── services.py (KPI calculation engine, time tracking metrics)
│   │   └── urls.py
│   ├── notifications/
│   │   ├── models.py (Notification, ActivityEvent)
│   │   ├── services.py (Event logger, Notification dispatcher)
│   │   ├── views.py (Notification list, mark read API)
│   │   └── urls.py
│   └── common/
│       ├── context_processors.py (workspace context, unread notifications, user role)
│       └── management/commands/seed_demo.py (Idempotent demo dataset)
├── templates/
│   ├── base.html
│   ├── components/ (sidebar, topbar, modals, status_badge, priority_badge, pagination)
│   ├── accounts/ (login.html, profile.html, users_admin.html)
│   ├── analytics/ (overview.html, reports.html, workload.html)
│   ├── projects/ (list.html, detail.html, form.html)
│   ├── tasks/ (board.html, list.html, calendar.html, gantt.html, my_tasks.html, detail.html, form.html)
│   ├── notifications/ (list.html)
│   └── errors/ (403.html, 404.html, 500.html)
├── static/
│   ├── css/ (app.css)
│   └── js/ (app.js, board.js, gantt.js, calendar.js)
└── tests/
    ├── test_auth_and_roles.py
    ├── test_tasks_and_crud.py
    ├── test_dependencies.py
    └── test_analytics_and_kpis.py
```

## 3. Implementation Phases
- **Phase 1: Foundation**: Project scaffold, `settings.py` with dynamic `DATABASE_URL` / SQLite fallback, modular apps, models, migrations, and `seed_demo` command.
- **Phase 2: Core Workflows**: Auth & role-based access control, Project/Task CRUD, My Tasks, List view (sortable/paginated), Kanban Board with drag-and-drop & API status persistence.
- **Phase 3: Dashboards & Analytics**: KPI calculation engine, Chart.js overview, drill-down filters, Team Workload matrix, Report generation & CSV export.
- **Phase 4: Planning & Deep Collaboration**: Subtasks, comments, attachments, time entries, activity feed, interactive Calendar and Gantt timeline with dependency links.
- **Phase 5: Refinements & Quality**: Polish UI/UX, notifications, unit/integration test suite, Vercel/Postgres deployment docs, and `IMPLEMENTATION_STATUS.md`.
