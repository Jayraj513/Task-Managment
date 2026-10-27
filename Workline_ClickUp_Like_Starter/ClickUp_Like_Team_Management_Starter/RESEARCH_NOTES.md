# Research Notes — ClickUp-inspired work management

Research checked 26 Oct 2026. Reference sources:
- ClickUp features: https://clickup.com/features
- ClickUp Gantt help: https://help.clickup.com/hc/en-us/articles/6310249474967-Create-and-share-a-Gantt-view
- Django install/database guidance: https://docs.djangoproject.com/en/4.2/topics/install/
- Django deployment checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ (confirm current docs version before deployment)

## Relevant patterns from ClickUp
ClickUp's public feature pages highlight task/project hierarchy, custom statuses and priorities, List/Board/Calendar/Gantt/Timeline/Workload views, dashboards, goals, time tracking, recurring work, templates, notifications and permissions. Gantt emphasizes timelines and task dependencies. Dashboards are valuable when cards drill into the underlying tasks.

## Recommended scope for our app
### P0 — must work in MVP
- Authentication and role-based permissions
- Workspace and projects
- Task CRUD with assignee, reporter, status, priority, start/due date, estimate, progress
- Subtasks, comments, attachments, tags, activity log
- List/table and Kanban board
- Manager dashboard and My Tasks dashboard
- Search, filters, sorting, pagination
- Seed demo data, admin screens, tests

### P1 — important after P0
- Calendar and Gantt with dependency links
- Team workload by user and week
- Time entries / time spent vs estimate
- Reports: overdue, completion trend, throughput, status aging, workload balance
- CSV export
- In-app notifications
- Project milestones

### P2 — later
- Recurring tasks, reusable templates, goals/OKRs
- Email notifications, saved filters, configurable custom fields
- Scheduled dashboard reports, integrations, AI summaries

## Dashboard KPIs
- Total open tasks
- Completed this week
- Overdue tasks
- Blocked tasks
- Completion rate
- Tasks by status and priority
- Tasks by assignee
- Workload vs estimate per person
- Completion trend over time
- Tasks with no owner or no due date

Every KPI needs a documented definition. Example: overdue = due date before today AND status not in completed/cancelled. Completion rate = completed tasks / all non-cancelled tasks for selected scope and period.

## UX principles
- Clean, professional, modern, responsive.
- Left sidebar, top global search, quick-create task button, compact cards, charts, and a clear “My Work” page.
- Avoid feature overload: simple defaults, advanced options where useful.
- All views share the same database-backed task filters.
- Include empty states, loading states, form validation and useful error messages.
- Use accessible contrast, keyboard focus states and responsive layout.

## Database and deployment finding
Django officially supports SQLite and PostgreSQL. SQLite is convenient for local prototyping, but for a multi-user hosted system use managed PostgreSQL. A deployed app's local filesystem may be ephemeral; do not store production database state in a SQLite file inside a Vercel deployment. If Vercel is retained, choose and verify a compatible Django runtime/adapter and use external managed PostgreSQL. If the Django runtime proves awkward, recommend a stable Python host rather than sacrificing reliability.

## Licensing
Before selecting any Gantt/calendar/drag-and-drop dependency, check its current license, maintenance activity, and production usage terms. Do not copy ClickUp branding, assets, or proprietary UI.
