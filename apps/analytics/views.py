import csv
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q

from apps.workspaces.models import Workspace
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus, TaskPriority, TimeEntry
from apps.analytics.services import (
    get_filtered_tasks_queryset,
    calculate_dashboard_kpis,
    get_status_distribution,
    get_priority_distribution,
    get_assignee_distribution,
    get_completion_trend,
    get_team_workload_matrix
)


@login_required
def overview_dashboard_view(request):
    """
    Overview Dashboard: Real-time query-backed KPIs, Chart.js analytics,
    recently updated tasks, and interactive filter controls.
    """
    workspace = getattr(request, 'current_workspace', None) or Workspace.objects.first()

    # Get filter query params
    params = request.GET.dict()
    tasks_qs = get_filtered_tasks_queryset(workspace, params)

    # Calculate KPIs and Chart data
    kpis = calculate_dashboard_kpis(tasks_qs)
    status_chart = get_status_distribution(tasks_qs)
    priority_chart = get_priority_distribution(tasks_qs)
    assignee_chart = get_assignee_distribution(workspace, tasks_qs)
    trend_chart = get_completion_trend(tasks_qs, days=14)

    # Recently updated tasks
    recent_tasks = tasks_qs.order_by('-updated_at')[:8]

    # Filter dropdown options
    projects = Project.objects.filter(workspace=workspace, archived_at__isnull=True).order_by('name')
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct().order_by('first_name', 'username')

    return render(request, 'analytics/overview.html', {
        'workspace': workspace,
        'projects': projects,
        'users': users,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'kpis': kpis,
        'status_chart_json': json.dumps(status_chart),
        'priority_chart_json': json.dumps(priority_chart),
        'assignee_chart_json': json.dumps(assignee_chart),
        'trend_chart_json': json.dumps(trend_chart),
        'recent_tasks': recent_tasks,
        'selected_project': params.get('project', 'all'),
        'selected_assignee': params.get('assignee', 'all'),
        'selected_status': params.get('status', 'all'),
        'selected_priority': params.get('priority', 'all'),
        'date_from': params.get('date_from', ''),
        'date_to': params.get('date_to', ''),
        'today': timezone.localdate(),
    })


@login_required
def team_workload_view(request):
    """
    Team Workload: Weekly capacity vs estimated task hours matrix.
    Identifies overload using documented configurable capacity per member.
    """
    workspace = getattr(request, 'current_workspace', None) or Workspace.objects.first()
    workload_matrix = get_team_workload_matrix(workspace)

    # Summary totals
    total_capacity = sum(m['capacity_hours'] for m in workload_matrix)
    total_estimated = sum(m['estimated_hours'] for m in workload_matrix)
    total_logged = sum(m['logged_hours'] for m in workload_matrix)
    total_overloaded_members = sum(1 for m in workload_matrix if m['is_overloaded'])

    overall_utilization = int(round((total_estimated / total_capacity) * 100)) if total_capacity > 0 else 0

    return render(request, 'analytics/workload.html', {
        'workspace': workspace,
        'workload_matrix': workload_matrix,
        'total_capacity': total_capacity,
        'total_estimated': round(total_estimated, 1),
        'total_logged': round(total_logged, 1),
        'total_overloaded_members': total_overloaded_members,
        'overall_utilization': overall_utilization,
    })


@login_required
def reports_view(request):
    """
    Detailed analytical reports:
    - Overdue tasks report
    - Completed tasks by team member
    - Estimate vs actual logged time per project
    - Unassigned tasks
    """
    workspace = getattr(request, 'current_workspace', None) or Workspace.objects.first()
    today = timezone.localdate()

    # 1. Overdue tasks
    overdue_tasks = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        due_date__lt=today
    ).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]).select_related('project', 'assignee')

    # 2. Member performance breakdown
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct()
    member_reports = []
    for u in users:
        u_tasks = Task.objects.filter(project__workspace=workspace, assignee=u, archived_at__isnull=True)
        completed = u_tasks.filter(status=TaskStatus.DONE).count()
        in_progress = u_tasks.filter(status=TaskStatus.IN_PROGRESS).count()
        overdue = u_tasks.filter(due_date__lt=today).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]).count()
        logged_hours = TimeEntry.objects.filter(task__project__workspace=workspace, user=u).aggregate(total=Sum('duration_hours'))['total'] or 0.0

        member_reports.append({
            'user': u,
            'completed': completed,
            'in_progress': in_progress,
            'overdue': overdue,
            'logged_hours': round(float(logged_hours), 1),
        })

    # 3. Project Estimate vs Actual Logged Time
    projects = Project.objects.filter(workspace=workspace, archived_at__isnull=True)
    project_time_reports = []
    for p in projects:
        p_tasks = p.tasks.filter(archived_at__isnull=True)
        est = p_tasks.aggregate(total=Sum('estimate_hours'))['total'] or 0.0
        actual = TimeEntry.objects.filter(task__project=p).aggregate(total=Sum('duration_hours'))['total'] or 0.0

        variance = float(est) - float(actual)
        project_time_reports.append({
            'project': p,
            'estimated_hours': round(float(est), 1),
            'actual_hours': round(float(actual), 1),
            'variance_hours': round(variance, 1),
        })

    # 4. Unassigned tasks
    unassigned_tasks = Task.objects.filter(
        project__workspace=workspace,
        archived_at__isnull=True,
        assignee__isnull=True
    ).exclude(status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]).select_related('project')

    return render(request, 'analytics/reports.html', {
        'workspace': workspace,
        'overdue_tasks': overdue_tasks,
        'member_reports': member_reports,
        'project_time_reports': project_time_reports,
        'unassigned_tasks': unassigned_tasks,
    })


@login_required
def export_tasks_csv_view(request):
    """
    Exports filtered tasks as a CSV file.
    Respects all active filter parameters from the user's current view.
    """
    workspace = getattr(request, 'current_workspace', None) or Workspace.objects.first()
    params = request.GET.dict()
    tasks_qs = get_filtered_tasks_queryset(workspace, params)

    response = HttpResponse(content_type='text/csv')
    filename = f"workline-tasks-export-{timezone.localdate().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Identifier',
        'Title',
        'Project',
        'Status',
        'Priority',
        'Assignee',
        'Reporter',
        'Start Date',
        'Due Date',
        'Estimated Hours',
        'Progress (%)',
        'Tags',
        'Created At'
    ])

    for t in tasks_qs:
        writer.writerow([
            t.identifier,
            t.title,
            t.project.name,
            t.get_status_display(),
            t.get_priority_display(),
            (t.assignee.get_full_name() or t.assignee.username) if t.assignee else 'Unassigned',
            t.reporter.get_full_name() or t.reporter.username,
            t.start_date.strftime('%Y-%m-%d') if t.start_date else '',
            t.due_date.strftime('%Y-%m-%d') if t.due_date else '',
            float(t.estimate_hours),
            t.progress_percent,
            ', '.join([tag.name for tag in t.tags.all()]),
            t.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response
