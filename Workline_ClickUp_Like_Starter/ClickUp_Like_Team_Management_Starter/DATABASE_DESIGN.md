# Initial Database Design

This is a portable logical design; Antigravity should refine it and generate Django models/migrations.

## Entities
- User: Django user model; role/profile; active flag.
- Workspace: name, timezone, created_by.
- WorkspaceMembership: workspace, user, role, joined_at.
- Project: workspace, name, key, description, owner, status, start_date, due_date, archived_at.
- ProjectMembership: project, user, project_role.
- Task: project, title, description, status, priority, assignee, reporter, start_date, due_date, estimate_minutes, progress_percent, parent_task, blocked_reason, archived_at, created_at, updated_at.
- Tag: workspace, name, color; TaskTag join table.
- TaskDependency: predecessor_task, successor_task, dependency_type; unique pair; prevent self-dependency and cycles.
- Comment: task, author, body, created_at, updated_at.
- Attachment: task, uploaded_by, file, original_filename, content_type, size_bytes, created_at.
- ActivityEvent: workspace, actor, project, task, event_type, summary, metadata JSON, created_at.
- Milestone: project, name, due_date, status, linked_task optional.
- TimeEntry: task, user, started_at, ended_at or duration_minutes, note, approved_by optional.
- Notification: recipient, actor optional, task optional, event_type, read_at, created_at.
- SavedFilter (optional): user, name, serialized validated filter settings.
- Goal (P1/P2): workspace, title, target_value, current_value, due_date, owner, status.

## Constraints and indexes
- Project key unique within workspace.
- progress_percent 0–100.
- due_date >= start_date when both supplied.
- TaskDependency predecessor != successor; unique pair; validate acyclic graph in service layer.
- Index Task(project,status), Task(assignee,status), Task(due_date,status), Task(priority,status), ActivityEvent(task,created_at).
- Use timezone-aware datetimes.
- Choose on_delete behaviors deliberately; prefer PROTECT/SET_NULL for audit-sensitive records, CASCADE only for true owned children.
