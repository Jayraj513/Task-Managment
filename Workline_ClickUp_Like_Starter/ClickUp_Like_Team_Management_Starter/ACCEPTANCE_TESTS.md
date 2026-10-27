# Acceptance Test Checklist

## Authentication and access
- [ ] Anonymous user is redirected to login for private pages.
- [ ] User can log in and log out.
- [ ] Member cannot access admin-only endpoints by typing URLs directly.
- [ ] Viewer cannot mutate tasks/projects.
- [ ] User outside a project cannot read its private task data.

## Projects and tasks
- [ ] Manager can create/edit/archive a project.
- [ ] Authorized user can create a task with owner, priority and dates.
- [ ] Invalid date range is rejected.
- [ ] Task status/priority updates persist after refresh.
- [ ] Assignee sees task under My Tasks.
- [ ] Subtask and comment appear in the correct task.
- [ ] Activity log records important updates.
- [ ] Dependencies reject self-links and cycles.

## Views
- [ ] Board drag/drop saves status and is permission checked.
- [ ] List sorting, filters and pagination work.
- [ ] Calendar tasks open the correct task.
- [ ] Gantt date edits persist if drag/resize is enabled.
- [ ] Filters produce consistent results across views.

## Dashboard and reports
- [ ] KPI values match task records in a known test dataset.
- [ ] Overdue excludes completed/cancelled tasks and handles date boundaries.
- [ ] Chart segments drill into the matching filtered tasks where implemented.
- [ ] Date/project/assignee filters update all applicable cards.
- [ ] CSV export respects active filters and permission scope.
- [ ] Empty data state does not crash or show misleading data.

## Operations
- [ ] Seed command is safe to run twice.
- [ ] `python manage.py check` passes.
- [ ] `python manage.py test` passes.
- [ ] `.env` and database files are ignored where appropriate.
- [ ] SQLite works locally.
- [ ] PostgreSQL config is tested against a real PostgreSQL instance before team launch.
- [ ] Deployment uses external persistent PostgreSQL, not a SQLite file on ephemeral storage.
