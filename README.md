# Workline — Team Task & Project Management Web Application

**Workline** is an original, high-performance, internal work and project management web application inspired by ClickUp. Designed for engineering and cross-functional teams, it provides deep task hierarchy, drag-and-drop Kanban boards, sortable lists, interactive Gantt timelines with dependency links, calendar views, personal workload dashboards, and real-time executive analytics.

---

## 1. Quick Start (Windows PowerShell)

Follow these exact steps from the project root directory (`d:\Task Management`):

### Step 1: Create and Activate Virtual Environment (Optional if Python 3.12 is active)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run Database Migrations
```powershell
python manage.py migrate
```

### Step 4: Seed Realistic Demo Data
Populates the demo workspace, 5 role-based user accounts, 3 projects, milestones, 28+ realistic tasks, subtasks, dependencies, time entries, and comments. This command is safe and idempotent (can be run repeatedly):
```powershell
python manage.py seed_demo
```

### Step 5: Collect Static Files
```powershell
python manage.py collectstatic --noinput
```

### Step 6: Start Local Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```

Open your browser to: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 2. Demo User Accounts

The login screen features **1-Click Quick Login** buttons to immediately test any role without typing passwords. For manual sign-in, all demo accounts use the standard password:

> **Universal Demo Password:** `WorklineDemo2026!`  
> *(Note: Clearly marked for demonstration only; must be changed before any shared or production rollout)*

| Name | Username / Email | Role | Permissions & Responsibilities |
| :--- | :--- | :--- | :--- |
| **Sarah Vance** | `admin` (`admin@workline.local`) | **Admin** | Full workspace administration, user roles, project settings, executive analytics. |
| **Marcus Brody** | `manager` (`manager@workline.local`) | **Manager** | Create & manage projects/tasks, review team workload, approve milestones. |
| **Alex Rivera** | `alex` (`alex@workline.local`) | **Member** | Senior Frontend: view assigned projects, update tasks, log time, comment. |
| **Maya Chen** | `maya` (`maya@workline.local`) | **Member** | Backend Systems: view assigned projects, update tasks, log time, comment. |
| **Taylor Jordan** | `taylor` (`taylor@workline.local`) | **Viewer** | Stakeholder / Auditor: Read-only access across approved dashboards & projects. |

---

## 3. Technology Stack

- **Backend:** Python 3.12 + Django 5.2
- **Frontend:** Django Templates + Tailwind CSS (via CDN) + Vanilla JavaScript
- **Static Assets:** WhiteNoise (compressed static file storage)
- **Analytics & Visualizations:** Chart.js (Doughnut, Bar, Stacked Bar, and Velocity Line charts)
- **Gantt & Dependencies:** Custom interactive SVG Gantt engine with acyclic dependency routing
- **Database:**
  - **Local Development:** SQLite 3 (Default, zero configuration at `BASE_DIR / 'db.sqlite3'`)
  - **Shared Pilot / Production:** PostgreSQL via `dj-database-url` and `psycopg` driver

---

## 4. Database Configuration & Production Switch

Workline provides a single, unified database configuration path in `workline/settings.py` adhering to twelve-factor methodology:

- **Local Development (No `DATABASE_URL`):**  
  Defaults automatically to SQLite at `d:\Task Management\db.sqlite3`.
- **Staging / Production (`DATABASE_URL` configured):**  
  When an environment variable `DATABASE_URL` starting with `postgresql://` or `postgres://` is provided, Django parses it via `dj_database_url` using the high-performance `psycopg` driver with persistent connection pooling (`conn_max_age=600`).

### Switching to PostgreSQL Without Code Changes
1. Provision a managed PostgreSQL instance (e.g. Neon, Supabase, AWS RDS, Azure Database for PostgreSQL).
2. Set the `DATABASE_URL` in your `.env` or cloud hosting environment:
   ```env
   DATABASE_URL=postgresql://workline_user:YourStrongPassword@ep-your-db-host.postgres.database.azure.com:5432/worklinedb?sslmode=require
   ```
3. Run migrations on the new database:
   ```powershell
   python manage.py migrate
   python manage.py seed_demo
   ```
4. **Data Migration Checklist (SQLite -> PostgreSQL):**
   - Do not simply swap the URL if you wish to retain custom local tasks.
   - Use `python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data_backup.json` to export from SQLite.
   - Switch `DATABASE_URL` to PostgreSQL and run `python manage.py migrate`.
   - Import data with `python manage.py loaddata data_backup.json`.

---

## 5. Deployment Architecture & Hosting Assessment

### Vercel Deployment Evaluation
> [!IMPORTANT]
> **Vercel Runtime Blocker Analysis:**
> - Vercel is optimized for frontend frameworks and ephemeral Node.js/Edge serverless functions.
> - **SQLite is strictly incompatible with Vercel:** Serverless execution environments have ephemeral, read-only filesystems. Any write to a local SQLite file is either forbidden or immediately lost when the lambda container spins down.
> - While community WSGI bridges exist for Django on Vercel, serverless cold starts, ephemeral local file storage (disabling user media file uploads without S3), and background job constraints make long-running team task management unreliable.

### Recommended Production Python Hosting
For a robust team rollout of Workline, deploy using a persistent container-friendly platform:
1. **Render.com / Railway.app / Fly.io:**
   - Native Python 3.12 runtime with Gunicorn.
   - Managed PostgreSQL database in the same region.
   - Persistent volume support for media file attachments (or direct S3 storage via `django-storages`).
   - Webhook-driven CI/CD directly from GitHub.
2. **AWS App Runner / Azure Container Apps:**
   - Production enterprise scaling with managed PostgreSQL (AWS RDS / Azure Postgres).

---

## 6. Running Automated Tests & Verification

Workline includes comprehensive unit and smoke test suites:

### Run the Django Automated Test Suite:
```powershell
python manage.py test tests
```
*Validates 18 unit tests across authentication boundaries, role mutations, CRUD validation, acyclic dependency detection, and KPI arithmetic.*

### Run the End-to-End HTTP Smoke Test:
```powershell
python test_smoke.py
```
*Validates all 16 private and administrative endpoints under authenticated sessions, verifying HTTP 200 OK responses and proper template rendering.*

---

## 7. Project Architecture & File Tree

```
d:\Task Management/
├── manage.py                          # Django management script
├── requirements.txt                   # Production Python dependencies
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git exclusion rules
├── ARCHITECTURE_PLAN.md               # Architecture design & specifications
├── IMPLEMENTATION_STATUS.md           # Audit status & feature checklist
├── README.md                          # Project documentation (this file)
├── test_smoke.py                      # Automated HTTP smoke test script
├── workline/                          # Project core package
│   ├── settings.py                    # Dual SQLite / PostgreSQL configuration
│   ├── urls.py                        # Root URL routing & error handlers
│   ├── wsgi.py                        # WSGI server entrypoint
│   └── asgi.py                        # ASGI server entrypoint
├── apps/                              # Modular domain applications
│   ├── accounts/                      # User profile, roles, authentication
│   ├── workspaces/                    # Workspace & multi-tenant settings
│   ├── projects/                      # Projects, memberships, milestones
│   ├── tasks/                         # Tasks, Kanban, Gantt, subtasks, tags, dependencies
│   ├── analytics/                     # Overview dashboard, reports, workload, CSV export
│   ├── notifications/                 # In-app notifications & activity logging
│   └── common/                        # Seed command, context processors, error views
├── templates/                         # Django HTML templates
│   ├── base.html                      # Main layout shell (Tailwind & Inter)
│   ├── components/                    # Sidebar, Topbar, Modals
│   ├── accounts/                      # Login, Profile, User Administration, Workspace Settings
│   ├── projects/                      # Project List, Detail, Form
│   ├── tasks/                         # Board, List, My Tasks, Calendar, Gantt, Detail, Form
│   ├── analytics/                     # Overview Dashboard, Team Workload, Reports
│   ├── notifications/                 # Notifications List
│   └── errors/                        # 403, 404, 500 error views
└── static/                            # Static CSS, JS, and icons
    ├── css/app.css                    # Design system tokens, chips, drag & drop styles
    └── js/app.js                      # CSRF handling, Kanban drag/drop, keyboard shortcuts
```
