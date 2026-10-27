"""
Analytics and KPI computation service for Workline.
All metrics are query-backed from the database and respect user filters.
Documentation of KPI definitions:
- Total Open Tasks: Active tasks (archived_at is NULL, parent_task is NULL) where status NOT IN ('DONE', 'CANCELLED').
- Completed This Week: Tasks with status='DONE' updated or completed on or after start of current week (Monday).
- Overdue Tasks: Tasks where due_date < today AND status NOT IN ('DONE', 'CANCELLED').
- Blocked Tasks: Active tasks where status = 'BLOCKED'.
- Unassigned Tasks: Active open tasks where assignee IS NULL.
- Completion Rate: (Completed tasks / (Total active tasks - Cancelled tasks)) * 100, safely handled when denominator is 0.
- Workload Capacity: Total estimated hours allocated to user for active work compared to weekly_capacity_hours (default 40h).
"""

from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.tasks.models import Task, TaskStatus, TaskPriority, TimeEntry
from apps.projects.models import Project
from apps.accounts.models import UserProfile
from django.contrib.auth.models import User


def get_filtered_tasks_queryset(workspace, params=None):
    """
    Returns base Task queryset for a workspace filtered by query parameters:
    - project_id
    - assignee_id
    - status
    - priority
    - due_date_from, due_date_to
    - search query (q)
    Excludes soft-deleted/archived tasks and top-level subtasks unless specified.
    """
    qs = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        parent_task__isnull=True # Top-level tasks for dashboard metrics
    ).select_related('project', 'assignee', 'reporter').prefetch_related('tags')

    if not params:
        return qs

    project_id = params.get('project')
    if project_id and project_id != 'all':
        qs = qs.filter(project_id=project_id)

    assignee_id = params.get('assignee')
    if assignee_id and assignee_id != 'all':
        if assignee_id == 'unassigned':
            qs = qs.filter(assignee__isnull=True)
        else:
            qs = qs.filter(assignee_id=assignee_id)

    status = params.get('status')
    if status and status != 'all':
        qs = qs.filter(status=status)

    priority = params.get('priority')
    if priority and priority != 'all':
        qs = qs.filter(priority=priority)

    date_from = params.get('date_from')
    if date_from:
        qs = qs.filter(due_date__gte=date_from)

    date_to = params.get('date_to')
    if date_to:
        qs = qs.filter(due_date__lte=date_to)

    q = params.get('q')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    return qs


def calculate_dashboard_kpis(tasks_qs):
    """
    Computes summary KPI dictionary from the filtered tasks queryset.
    """
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())

    total_count = tasks_qs.count()
    completed_count = tasks_qs.filter(status=TaskStatus.DONE).count()
    cancelled_count = tasks_qs.filter(status=TaskStatus.CANCELLED).count()

    open_tasks = tasks_qs.exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED])
    total_open = open_tasks.count()

    completed_this_week = tasks_qs.filter(
        status=TaskStatus.DONE,
        updated_at__date__gte=start_of_week
    ).count()

    overdue_count = open_tasks.filter(due_date__lt=today).count()
    blocked_count = tasks_qs.filter(status=TaskStatus.BLOCKED).count()
    unassigned_count = open_tasks.filter(assignee__isnull=True).count()

    denominator = total_count - cancelled_count
    if denominator > 0:
        completion_rate = int(round((completed_count / denominator) * 100))
    else:
        completion_rate = 100 if completed_count > 0 else 0

    return {
        'total_tasks': total_count,
        'total_open': total_open,
        'completed_this_week': completed_this_week,
        'completed_total': completed_count,
        'overdue_count': overdue_count,
        'blocked_count': blocked_count,
        'unassigned_count': unassigned_count,
        'completion_rate': completion_rate,
    }


def get_status_distribution(tasks_qs):
    """
    Distribution of tasks by status for Chart.js.
    """
    counts = dict(
        tasks_qs.values('status')
        .annotate(total=Count('id'))
        .values_list('status', 'total')
    )
    labels = []
    data = []
    colors = []
    color_map = {
        TaskStatus.BACKLOG: '#94a3b8',
        TaskStatus.TODO: '#64748b',
        TaskStatus.IN_PROGRESS: '#3b82f6',
        TaskStatus.IN_REVIEW: '#8b5cf6',
        TaskStatus.BLOCKED: '#ef4444',
        TaskStatus.DONE: '#10b981',
        TaskStatus.CANCELLED: '#cbd5e1',
    }

    for choice, label in TaskStatus.choices:
        labels.append(label)
        data.append(counts.get(choice, 0))
        colors.append(color_map.get(choice, '#6b7280'))

    return {
        'labels': labels,
        'data': data,
        'colors': colors,
    }


def get_priority_distribution(tasks_qs):
    """
    Distribution of tasks by priority for Chart.js.
    """
    counts = dict(
        tasks_qs.values('priority')
        .annotate(total=Count('id'))
        .values_list('priority', 'total')
    )
    labels = []
    data = []
    colors = []
    color_map = {
        TaskPriority.URGENT: '#dc2626',
        TaskPriority.HIGH: '#f97316',
        TaskPriority.MEDIUM: '#3b82f6',
        TaskPriority.LOW: '#64748b',
    }

    for choice, label in TaskPriority.choices:
        labels.append(label)
        data.append(counts.get(choice, 0))
        colors.append(color_map.get(choice, '#6b7280'))

    return {
        'labels': labels,
        'data': data,
        'colors': colors,
    }


def get_assignee_distribution(workspace, tasks_qs):
    """
    Task distribution by assignee for Chart.js and workload cards.
    """
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct()
    labels = []
    data_open = []
    data_done = []

    for user in users:
        full_name = user.get_full_name() or user.username
        labels.append(full_name)
        open_count = tasks_qs.filter(
            assignee=user
        ).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]).count()
        done_count = tasks_qs.filter(assignee=user, status=TaskStatus.DONE).count()
        data_open.append(open_count)
        data_done.append(done_count)

    # Unassigned bucket
    unassigned_open = tasks_qs.filter(
        assignee__isnull=True
    ).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]).count()
    if unassigned_open > 0:
        labels.append('Unassigned')
        data_open.append(unassigned_open)
        data_done.append(0)

    return {
        'labels': labels,
        'data_open': data_open,
        'data_done': data_done,
    }


def get_completion_trend(tasks_qs, days=14):
    """
    Daily completion trend for the last N days.
    """
    today = timezone.localdate()
    dates = [(today - timedelta(days=i)) for i in range(days - 1, -1, -1)]

    labels = [d.strftime('%b %d') for d in dates]
    created_counts = []
    completed_counts = []

    for d in dates:
        c_created = tasks_qs.filter(created_at__date=d).count()
        c_done = tasks_qs.filter(status=TaskStatus.DONE, updated_at__date=d).count()
        created_counts.append(c_created)
        completed_counts.append(c_done)

    return {
        'labels': labels,
        'created_counts': created_counts,
        'completed_counts': completed_counts,
    }


def get_team_workload_matrix(workspace):
    """
    Calculates weekly capacity vs assigned estimated hours for each team member.
    Identifies overload when estimated hours > weekly capacity.
    """
    users = User.objects.filter(
        workspace_memberships__workspace=workspace
    ).select_related('profile').distinct().order_by('first_name', 'username')

    matrix = []
    for user in users:
        profile = getattr(user, 'profile', None)
        capacity = profile.weekly_capacity_hours if profile else 40

        active_tasks = Task.objects.filter(
            project__workspace=workspace,
            assignee=user,
            archived_at__isnull=True
        ).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED])

        task_count = active_tasks.count()
        agg = active_tasks.aggregate(total_est=Sum('estimate_hours'))
        total_estimate = float(agg['total_est'] or 0.0)

        # Logged hours
        logged_agg = TimeEntry.objects.filter(
            task__project__workspace=workspace,
            user=user
        ).aggregate(total_logged=Sum('duration_hours'))
        total_logged = float(logged_agg['total_logged'] or 0.0)

        is_overloaded = total_estimate > capacity
        utilization_rate = int(round((total_estimate / capacity) * 100)) if capacity > 0 else 0

        matrix.append({
            'user': user,
            'profile': profile,
            'capacity_hours': capacity,
            'assigned_tasks_count': task_count,
            'estimated_hours': round(total_estimate, 1),
            'logged_hours': round(total_logged, 1),
            'is_overloaded': is_overloaded,
            'utilization_rate': utilization_rate,
            'remaining_capacity': max(0.0, round(capacity - total_estimate, 1)),
        })

    return matrix
