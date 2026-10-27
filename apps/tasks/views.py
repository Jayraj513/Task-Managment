import json
from decimal import Decimal
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, Sum

from apps.tasks.models import (
    Task, TaskStatus, TaskPriority, Tag, TaskDependency,
    DependencyType, Comment, Attachment, TimeEntry
)
from apps.projects.models import Project, Milestone
from apps.workspaces.models import Workspace
from apps.accounts.permissions import require_mutation_allowed, can_mutate_tasks
from apps.notifications.services import record_activity, notify_user
from apps.notifications.models import ActivityEventType
from apps.tasks.services import validate_dependency, detect_dependency_cycle


def _get_workspace_and_filters(request):
    workspace = getattr(request, 'current_workspace', None) or Workspace.objects.first()
    projects = Project.objects.filter(workspace=workspace, archived_at__isnull=True).order_by('name')
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct().order_by('first_name', 'username')
    tags = Tag.objects.filter(workspace=workspace).order_by('name')

    project_id = request.GET.get('project', 'all')
    assignee_id = request.GET.get('assignee', 'all')
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', 'all')
    q = request.GET.get('q', '').strip()

    return {
        'workspace': workspace,
        'projects': projects,
        'users': users,
        'tags': tags,
        'selected_project': project_id,
        'selected_assignee': assignee_id,
        'selected_status': status_filter,
        'selected_priority': priority_filter,
        'q': q,
    }


def _filter_tasks(qs, filters):
    if filters['selected_project'] != 'all':
        qs = qs.filter(project_id=filters['selected_project'])

    if filters['selected_assignee'] != 'all':
        if filters['selected_assignee'] == 'unassigned':
            qs = qs.filter(assignee__isnull=True)
        else:
            qs = qs.filter(assignee_id=filters['selected_assignee'])

    if filters['selected_status'] != 'all':
        qs = qs.filter(status=filters['selected_status'])

    if filters['selected_priority'] != 'all':
        qs = qs.filter(priority=filters['selected_priority'])

    if filters['q']:
        qs = qs.filter(Q(title__icontains=filters['q']) | Q(description__icontains=filters['q']))

    return qs


@login_required
def task_board_view(request):
    """
    Kanban Board View with columns for each TaskStatus.
    Interactive drag-and-drop and fallback dropdowns.
    """
    ctx_data = _get_workspace_and_filters(request)
    workspace = ctx_data['workspace']

    base_qs = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        parent_task__isnull=True
    ).select_related('project', 'assignee', 'reporter').prefetch_related('tags', 'subtasks')

    filtered_qs = _filter_tasks(base_qs, ctx_data)

    board_columns = []
    # Distinct columns to display on Kanban
    visible_statuses = [
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.IN_REVIEW,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
    ]

    for status_key in visible_statuses:
        status_tasks = [t for t in filtered_qs if t.status == status_key]
        board_columns.append({
            'status_key': status_key,
            'status_label': dict(TaskStatus.choices).get(status_key, status_key),
            'tasks': status_tasks,
            'count': len(status_tasks),
        })

    return render(request, 'tasks/board.html', {
        **ctx_data,
        'board_columns': board_columns,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
    })


@login_required
def task_list_view(request):
    """
    Table / List View with sortable columns, filters, and pagination.
    """
    ctx_data = _get_workspace_and_filters(request)
    workspace = ctx_data['workspace']

    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'title': 'title',
        '-title': '-title',
        'status': 'status',
        '-status': '-status',
        'priority': 'priority',
        '-priority': '-priority',
        'due_date': 'due_date',
        '-due_date': '-due_date',
        'progress': 'progress_percent',
        '-progress': '-progress_percent',
        'created': 'created_at',
        '-created': '-created_at',
    }
    sort_field = valid_sorts.get(sort_by, '-created_at')

    base_qs = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        parent_task__isnull=True
    ).select_related('project', 'assignee', 'reporter').prefetch_related('tags').order_by(sort_field)

    filtered_qs = _filter_tasks(base_qs, ctx_data)

    paginator = Paginator(filtered_qs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'tasks/list.html', {
        **ctx_data,
        'page_obj': page_obj,
        'sort_by': sort_by,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
    })


@login_required
def my_tasks_view(request):
    """
    My Tasks view for the current user.
    Grouped by Overdue, Today, Upcoming, and Completed.
    """
    today = timezone.localdate()
    my_tasks = Task.objects.filter(
        assignee=request.user,
        archived_at__isnull=True,
        parent_task__isnull=True
    ).select_related('project').prefetch_related('tags').order_by('due_date', '-priority')

    # Apply quick filter if any
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', 'all')

    if status_filter != 'all':
        my_tasks = my_tasks.filter(status=status_filter)
    if priority_filter != 'all':
        my_tasks = my_tasks.filter(priority=priority_filter)

    overdue_tasks = []
    today_tasks = []
    upcoming_tasks = []
    completed_tasks = []

    for t in my_tasks:
        if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            completed_tasks.append(t)
        elif t.due_date and t.due_date < today:
            overdue_tasks.append(t)
        elif t.due_date == today:
            today_tasks.append(t)
        else:
            upcoming_tasks.append(t)

    return render(request, 'tasks/my_tasks.html', {
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'upcoming_tasks': upcoming_tasks,
        'completed_tasks': completed_tasks,
        'selected_status': status_filter,
        'selected_priority': priority_filter,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'today': today,
    })


@login_required
def task_calendar_view(request):
    """
    Interactive Calendar View mapping tasks by due date.
    """
    ctx_data = _get_workspace_and_filters(request)
    workspace = ctx_data['workspace']

    # Month selection
    year = int(request.GET.get('year', timezone.localdate().year))
    month = int(request.GET.get('month', timezone.localdate().month))

    first_day_of_month = datetime(year, month, 1).date()
    if month == 12:
        next_month_date = datetime(year + 1, 1, 1).date()
    else:
        next_month_date = datetime(year, month + 1, 1).date()
    prev_month_date = (first_day_of_month - timedelta(days=1)).replace(day=1)

    # Start and end of the visible calendar matrix (including padding days)
    start_padding = first_day_of_month.weekday() # 0 = Monday
    grid_start_date = first_day_of_month - timedelta(days=start_padding)
    grid_end_date = grid_start_date + timedelta(days=41) # 6 weeks matrix

    tasks_qs = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        due_date__gte=grid_start_date,
        due_date__lte=grid_end_date
    ).select_related('project', 'assignee')

    tasks_qs = _filter_tasks(tasks_qs, ctx_data)

    # Group tasks by date
    tasks_by_date = {}
    for t in tasks_qs:
        date_str = t.due_date.strftime('%Y-%m-%d')
        tasks_by_date.setdefault(date_str, []).append(t)

    # Build calendar matrix
    calendar_days = []
    curr = grid_start_date
    while curr <= grid_end_date:
        date_str = curr.strftime('%Y-%m-%d')
        calendar_days.append({
            'date': curr,
            'date_str': date_str,
            'day_num': curr.day,
            'is_current_month': (curr.month == month),
            'is_today': (curr == timezone.localdate()),
            'tasks': tasks_by_date.get(date_str, []),
        })
        curr += timedelta(days=1)

    return render(request, 'tasks/calendar.html', {
        **ctx_data,
        'current_year': year,
        'current_month': month,
        'month_name': first_day_of_month.strftime('%B %Y'),
        'prev_year': prev_month_date.year,
        'prev_month': prev_month_date.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
        'calendar_days': calendar_days,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
    })


@login_required
def task_gantt_view(request):
    """
    Interactive Gantt Timeline View.
    Calculates timeline spans, dependency links and milestone pins.
    """
    ctx_data = _get_workspace_and_filters(request)
    workspace = ctx_data['workspace']

    tasks_qs = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        parent_task__isnull=True
    ).select_related('project', 'assignee').prefetch_related('successor_dependencies', 'predecessor_dependencies')

    tasks_qs = _filter_tasks(tasks_qs, ctx_data).order_by('start_date', 'due_date', 'id')

    # Milestones
    milestones_qs = Milestone.objects.filter(
        project__workspace=workspace
    ).select_related('project')
    if ctx_data['selected_project'] != 'all':
        milestones_qs = milestones_qs.filter(project_id=ctx_data['selected_project'])

    # Format JSON payload for interactive client-side rendering
    today = timezone.localdate()
    gantt_items = []
    dependencies_json = []

    for t in tasks_qs:
        s_date = t.start_date or (t.due_date - timedelta(days=3) if t.due_date else today)
        d_date = t.due_date or (s_date + timedelta(days=5))
        if d_date < s_date:
            d_date = s_date

        gantt_items.append({
            'id': t.id,
            'identifier': t.identifier,
            'title': t.title,
            'project_name': t.project.name,
            'project_color': t.project.color,
            'status': t.status,
            'status_display': t.get_status_display(),
            'priority': t.priority,
            'assignee': (t.assignee.get_full_name() or t.assignee.username) if t.assignee else 'Unassigned',
            'start': s_date.strftime('%Y-%m-%d'),
            'end': d_date.strftime('%Y-%m-%d'),
            'progress': t.progress_percent,
        })

    # Task dependencies for links
    deps = TaskDependency.objects.filter(
        predecessor_task__project__workspace=workspace,
        successor_task__project__workspace=workspace
    ).values('predecessor_task_id', 'successor_task_id', 'dependency_type')

    for d in deps:
        dependencies_json.append({
            'from': d['predecessor_task_id'],
            'to': d['successor_task_id'],
            'type': d['dependency_type'],
        })

    milestones_json = []
    for m in milestones_qs:
        milestones_json.append({
            'name': m.name,
            'project': m.project.name,
            'due_date': m.due_date.strftime('%Y-%m-%d'),
            'status': m.status,
        })

    return render(request, 'tasks/gantt.html', {
        **ctx_data,
        'gantt_tasks_json': json.dumps(gantt_items),
        'dependencies_json': json.dumps(dependencies_json),
        'milestones_json': json.dumps(milestones_json),
        'tasks_count': len(gantt_items),
    })


@login_required
def task_detail_view(request, task_id):
    """
    Task detail view / drawer with subtasks, comments, attachments,
    dependencies, time entries, and activity history.
    """
    task = get_object_or_404(
        Task.objects.select_related('project', 'assignee', 'reporter', 'parent_task'),
        id=task_id
    )

    subtasks = task.subtasks.filter(archived_at__isnull=True).select_related('assignee')
    comments = task.comments.select_related('author', 'author__profile').order_by('created_at')
    attachments = task.attachments.select_related('uploaded_by').order_by('-created_at')
    time_entries = task.time_entries.select_related('user').order_by('-entry_date', '-created_at')
    total_logged_hours = task.logged_hours_total

    # Dependencies: Predecessors (tasks this task depends on) & Successors (tasks blocked by this task)
    predecessor_deps = task.predecessor_dependencies.select_related('predecessor_task', 'predecessor_task__project')
    successor_deps = task.successor_dependencies.select_related('successor_task', 'successor_task__project')

    # Available tasks for adding a new dependency (exclude self and already linked)
    existing_pred_ids = predecessor_deps.values_list('predecessor_task_id', flat=True)
    potential_predecessors = Task.objects.filter(
        project__workspace=task.project.workspace,
        archived_at__isnull=True
    ).exclude(id=task.id).exclude(id__in=existing_pred_ids).order_by('title')

    # Activity events
    activity_events = task.activity_events.select_related('actor').order_by('-created_at')[:15]

    workspace_users = User.objects.filter(
        workspace_memberships__workspace=task.project.workspace
    ).distinct().order_by('first_name', 'username')

    return render(request, 'tasks/detail.html', {
        'task': task,
        'subtasks': subtasks,
        'comments': comments,
        'attachments': attachments,
        'time_entries': time_entries,
        'total_logged_hours': total_logged_hours,
        'predecessor_deps': predecessor_deps,
        'successor_deps': successor_deps,
        'potential_predecessors': potential_predecessors,
        'activity_events': activity_events,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'workspace_users': workspace_users,
    })


@require_mutation_allowed
def task_create_view(request):
    workspace = Workspace.objects.first()
    projects = Project.objects.filter(workspace=workspace, archived_at__isnull=True).order_by('name')
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct().order_by('first_name')
    tags = Tag.objects.filter(workspace=workspace).order_by('name')

    default_project_id = request.GET.get('project')
    parent_task_id = request.GET.get('parent')
    parent_task = Task.objects.filter(id=parent_task_id).first() if parent_task_id else None

    if request.method == 'POST':
        project_id = request.POST.get('project')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', TaskStatus.TODO)
        priority = request.POST.get('priority', TaskPriority.MEDIUM)
        assignee_id = request.POST.get('assignee')
        start_date = request.POST.get('start_date') or None
        due_date = request.POST.get('due_date') or None
        estimate_hours = request.POST.get('estimate_hours', '0.0')
        blocked_reason = request.POST.get('blocked_reason', '').strip()
        selected_tag_ids = request.POST.getlist('tags')

        errors = []
        if not title:
            errors.append("Task title is required.")

        project = Project.objects.filter(id=project_id).first()
        if not project:
            errors.append("Valid project is required.")

        if start_date and due_date and due_date < start_date:
            errors.append("Due date cannot be earlier than start date.")

        if status == TaskStatus.BLOCKED and not blocked_reason:
            errors.append("Please provide a blocked reason when status is Blocked.")

        try:
            est_val = Decimal(estimate_hours) if estimate_hours else Decimal('0.0')
        except Exception:
            est_val = Decimal('0.0')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'tasks/form.html', {
                'projects': projects,
                'users': users,
                'tags': tags,
                'status_choices': TaskStatus.choices,
                'priority_choices': TaskPriority.choices,
                'action_title': 'Create Task',
                'selected_project_id': project_id,
            })

        assignee = User.objects.filter(id=assignee_id).first() if assignee_id else None

        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            reporter=request.user,
            start_date=start_date,
            due_date=due_date,
            estimate_hours=est_val,
            parent_task=parent_task,
            blocked_reason=blocked_reason if status == TaskStatus.BLOCKED else '',
        )

        if selected_tag_ids:
            task.tags.set(Tag.objects.filter(id__in=selected_tag_ids, workspace=workspace))

        # Record activity event
        record_activity(
            workspace=workspace,
            actor=request.user,
            event_type=ActivityEventType.TASK_CREATED,
            summary=f"{request.user.get_full_name() or request.user.username} created task {task.identifier}",
            project=project,
            task=task
        )

        # Notify assignee if someone else assigned it
        if assignee and assignee != request.user:
            notify_user(
                recipient=assignee,
                actor=request.user,
                task=task,
                project=project,
                event_type='TASK_ASSIGNED',
                title=f"New Task Assigned: {task.identifier}",
                message=f"{request.user.get_full_name() or request.user.username} assigned you to '{task.title}'",
                link_url=f"/tasks/{task.id}/"
            )

        messages.success(request, f"Task {task.identifier} created successfully.")
        return redirect('task_detail', task_id=task.id)

    return render(request, 'tasks/form.html', {
        'projects': projects,
        'users': users,
        'tags': tags,
        'parent_task': parent_task,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'action_title': 'Create Task',
        'selected_project_id': default_project_id or (parent_task.project_id if parent_task else None),
    })


@require_mutation_allowed
def task_edit_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    workspace = task.project.workspace
    projects = Project.objects.filter(workspace=workspace, archived_at__isnull=True).order_by('name')
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct().order_by('first_name')
    tags = Tag.objects.filter(workspace=workspace).order_by('name')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', task.status)
        priority = request.POST.get('priority', task.priority)
        assignee_id = request.POST.get('assignee')
        start_date = request.POST.get('start_date') or None
        due_date = request.POST.get('due_date') or None
        estimate_hours = request.POST.get('estimate_hours', '0.0')
        progress_percent = request.POST.get('progress_percent', '0')
        blocked_reason = request.POST.get('blocked_reason', '').strip()
        selected_tag_ids = request.POST.getlist('tags')

        if not title:
            messages.error(request, "Task title is required.")
            return redirect('task_edit', task_id=task.id)

        if start_date and due_date and due_date < start_date:
            messages.error(request, "Due date cannot be earlier than start date.")
            return redirect('task_edit', task_id=task.id)

        if status == TaskStatus.BLOCKED and not blocked_reason:
            messages.error(request, "Please specify why this task is blocked.")
            return redirect('task_edit', task_id=task.id)

        try:
            est_val = Decimal(estimate_hours) if estimate_hours else Decimal('0.0')
        except Exception:
            est_val = task.estimate_hours

        try:
            prog_val = max(0, min(100, int(progress_percent)))
        except Exception:
            prog_val = task.progress_percent

        old_assignee = task.assignee
        old_status = task.status
        new_assignee = User.objects.filter(id=assignee_id).first() if assignee_id else None

        task.title = title
        task.description = description
        task.status = status
        task.priority = priority
        task.assignee = new_assignee
        task.start_date = start_date
        task.due_date = due_date
        task.estimate_hours = est_val
        task.progress_percent = prog_val
        task.blocked_reason = blocked_reason if status == TaskStatus.BLOCKED else ''
        task.save()

        task.tags.set(Tag.objects.filter(id__in=selected_tag_ids, workspace=workspace))

        # Check for status change
        if old_status != status:
            record_activity(
                workspace=workspace,
                actor=request.user,
                event_type=ActivityEventType.STATUS_CHANGED,
                summary=f"{request.user.get_full_name() or request.user.username} moved {task.identifier} to {task.get_status_display()}",
                project=task.project,
                task=task,
                metadata={'old_status': old_status, 'new_status': status}
            )

        # Check for assignee change
        if old_assignee != new_assignee:
            record_activity(
                workspace=workspace,
                actor=request.user,
                event_type=ActivityEventType.ASSIGNED,
                summary=f"{request.user.get_full_name() or request.user.username} assigned {task.identifier} to {(new_assignee.get_full_name() or new_assignee.username) if new_assignee else 'Unassigned'}",
                project=task.project,
                task=task
            )
            if new_assignee and new_assignee != request.user:
                notify_user(
                    recipient=new_assignee,
                    actor=request.user,
                    task=task,
                    project=task.project,
                    event_type='TASK_ASSIGNED',
                    title=f"Assigned to {task.identifier}",
                    message=f"You were assigned to '{task.title}'",
                    link_url=f"/tasks/{task.id}/"
                )

        messages.success(request, f"Task {task.identifier} updated successfully.")
        return redirect('task_detail', task_id=task.id)

    return render(request, 'tasks/form.html', {
        'task': task,
        'projects': projects,
        'users': users,
        'tags': tags,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'action_title': f"Edit Task: {task.identifier}",
        'selected_project_id': task.project_id,
    })


@require_mutation_allowed
@require_POST
def api_update_task_status(request, task_id):
    """
    AJAX endpoint for Drag & Drop Kanban board and inline table status updates.
    Enforces server-side permissions and logs audit activity.
    """
    task = get_object_or_404(Task, id=task_id)

    # Parse JSON or form body
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        new_status = data.get('status')
    else:
        new_status = request.POST.get('status')

    if new_status not in TaskStatus.values:
        return JsonResponse({'success': False, 'error': 'Invalid status value.'}, status=400)

    old_status = task.status
    if old_status == new_status:
        return JsonResponse({'success': True, 'status': new_status})

    task.status = new_status
    if new_status == TaskStatus.DONE:
        task.progress_percent = 100
    elif new_status == TaskStatus.TODO and task.progress_percent == 100:
        task.progress_percent = 0

    task.save()

    record_activity(
        workspace=task.project.workspace,
        actor=request.user,
        event_type=ActivityEventType.STATUS_CHANGED,
        summary=f"{request.user.get_full_name() or request.user.username} updated status of {task.identifier} to {task.get_status_display()}",
        project=task.project,
        task=task,
        metadata={'old_status': old_status, 'new_status': new_status}
    )

    # Notify assignee if someone else changed their task status
    if task.assignee and task.assignee != request.user:
        notify_user(
            recipient=task.assignee,
            actor=request.user,
            task=task,
            project=task.project,
            event_type='STATUS_CHANGED',
            title=f"Status Updated: {task.identifier}",
            message=f"{request.user.get_full_name() or request.user.username} moved '{task.title}' to {task.get_status_display()}",
            link_url=f"/tasks/{task.id}/"
        )

    return JsonResponse({
        'success': True,
        'task_id': task.id,
        'identifier': task.identifier,
        'new_status': new_status,
        'status_display': task.get_status_display(),
        'progress_percent': task.progress_percent,
    })


@require_mutation_allowed
def task_archive_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        if task.is_archived:
            task.archived_at = None
            msg = f"Task {task.identifier} restored from archive."
        else:
            task.archived_at = timezone.now()
            msg = f"Task {task.identifier} archived."
        task.save()

        record_activity(
            workspace=task.project.workspace,
            actor=request.user,
            event_type=ActivityEventType.TASK_CREATED,
            summary=msg,
            project=task.project,
            task=task
        )

        messages.info(request, msg)
        return redirect('task_list')

    return redirect('task_detail', task_id=task.id)


@require_mutation_allowed
@require_POST
def task_add_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    body = request.POST.get('body', '').strip()

    if body:
        comment = Comment.objects.create(
            task=task,
            author=request.user,
            body=body
        )

        record_activity(
            workspace=task.project.workspace,
            actor=request.user,
            event_type=ActivityEventType.COMMENTED,
            summary=f"{request.user.get_full_name() or request.user.username} commented on {task.identifier}",
            project=task.project,
            task=task
        )

        # Notify assignee & reporter
        recipients = {task.assignee, task.reporter} - {request.user, None}
        for rec in recipients:
            notify_user(
                recipient=rec,
                actor=request.user,
                task=task,
                project=task.project,
                event_type='NEW_COMMENT',
                title=f"New comment on {task.identifier}",
                message=f"{request.user.get_full_name() or request.user.username}: \"{body[:80]}...\"",
                link_url=f"/tasks/{task.id}/"
            )

        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Comment cannot be empty.")

    return redirect('task_detail', task_id=task.id)


@require_mutation_allowed
@require_POST
def task_add_time_entry(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    duration = request.POST.get('duration_hours')
    entry_date = request.POST.get('entry_date') or timezone.localdate()
    note = request.POST.get('note', '').strip()

    try:
        duration_val = Decimal(duration)
        if duration_val <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "Please enter a valid duration in hours (e.g. 1.5).")
        return redirect('task_detail', task_id=task.id)

    TimeEntry.objects.create(
        task=task,
        user=request.user,
        duration_hours=duration_val,
        entry_date=entry_date,
        note=note
    )

    record_activity(
        workspace=task.project.workspace,
        actor=request.user,
        event_type=ActivityEventType.TIME_LOGGED,
        summary=f"{request.user.get_full_name() or request.user.username} logged {duration_val}h on {task.identifier}",
        project=task.project,
        task=task,
        metadata={'hours': float(duration_val)}
    )

    messages.success(request, f"Logged {duration_val} hours.")
    return redirect('task_detail', task_id=task.id)


@require_mutation_allowed
@require_POST
def task_add_attachment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    uploaded_file = request.FILES.get('attachment_file')

    if not uploaded_file:
        messages.error(request, "No file selected for upload.")
        return redirect('task_detail', task_id=task.id)

    # Enforce 10MB file limit
    if uploaded_file.size > 10 * 1024 * 1024:
        messages.error(request, "File size exceeds the 10MB limit.")
        return redirect('task_detail', task_id=task.id)

    attachment = Attachment.objects.create(
        task=task,
        uploaded_by=request.user,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        content_type=uploaded_file.content_type or 'application/octet-stream',
        size_bytes=uploaded_file.size
    )

    messages.success(request, f"Attached '{uploaded_file.name}' ({attachment.formatted_size}).")
    return redirect('task_detail', task_id=task.id)


@require_mutation_allowed
@require_POST
def task_add_dependency(request, task_id):
    successor_task = get_object_or_404(Task, id=task_id)
    predecessor_id = request.POST.get('predecessor_task_id')
    dependency_type = request.POST.get('dependency_type', DependencyType.BLOCKS)

    if not predecessor_id:
        messages.error(request, "Please select a task.")
        return redirect('task_detail', task_id=task_id)

    predecessor_task = get_object_or_404(Task, id=predecessor_id)

    try:
        validate_dependency(predecessor_task, successor_task, TaskDependency)
        TaskDependency.objects.create(
            predecessor_task=predecessor_task,
            successor_task=successor_task,
            dependency_type=dependency_type
        )
        record_activity(
            workspace=successor_task.project.workspace,
            actor=request.user,
            event_type=ActivityEventType.DEPENDENCY_ADDED,
            summary=f"Linked dependency: {predecessor_task.identifier} -> {successor_task.identifier}",
            project=successor_task.project,
            task=successor_task
        )
        messages.success(request, f"Dependency added: '{predecessor_task.title}' now blocks '{successor_task.title}'.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return redirect('task_detail', task_id=task_id)


@require_mutation_allowed
@require_POST
def task_delete_dependency(request, dependency_id):
    dep = get_object_or_404(TaskDependency, id=dependency_id)
    successor_id = dep.successor_task_id
    dep.delete()
    messages.info(request, "Dependency link removed.")
    return redirect('task_detail', task_id=successor_id)


@require_mutation_allowed
@require_POST
def task_quick_create_api(request):
    """
    Quick-create task modal handler from the top navigation bar.
    """
    workspace = Workspace.objects.first()
    title = request.POST.get('title', '').strip()
    project_id = request.POST.get('project')
    priority = request.POST.get('priority', TaskPriority.MEDIUM)
    due_date = request.POST.get('due_date') or None

    if not title or not project_id:
        messages.error(request, "Task title and project are required for quick create.")
        return redirect(request.META.get('HTTP_REFERER', 'overview'))

    project = get_object_or_404(Project, id=project_id)
    task = Task.objects.create(
        project=project,
        title=title,
        status=TaskStatus.TODO,
        priority=priority,
        reporter=request.user,
        due_date=due_date
    )

    record_activity(
        workspace=workspace,
        actor=request.user,
        event_type=ActivityEventType.TASK_CREATED,
        summary=f"{request.user.get_full_name() or request.user.username} created task {task.identifier}",
        project=project,
        task=task
    )

    messages.success(request, f"Task {task.identifier} created successfully.")
    return redirect('task_detail', task_id=task.id)
