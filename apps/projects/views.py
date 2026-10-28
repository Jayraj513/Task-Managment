from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.core.exceptions import ValidationError

from apps.projects.models import Project, ProjectStatus, Milestone, MilestoneStatus, ProjectMembership
from apps.workspaces.models import Workspace
from apps.workspaces.services import get_active_workspace
from apps.tasks.models import Task, TaskStatus
from apps.accounts.permissions import require_manager_or_above, can_manage_projects
from apps.notifications.services import record_activity
from apps.notifications.models import ActivityEventType
from django.contrib.auth.models import User


@login_required
def project_list_view(request):
    workspace = getattr(request, 'current_workspace', None) or get_active_workspace(request)

    show_archived = request.GET.get('archived') == '1'
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    projects_qs = Project.objects.filter(workspace=workspace).select_related('owner')

    if show_archived:
        projects_qs = projects_qs.filter(Q(status=ProjectStatus.ARCHIVED) | Q(archived_at__isnull=False))
    else:
        projects_qs = projects_qs.exclude(status=ProjectStatus.ARCHIVED).filter(archived_at__isnull=True)

    if status_filter != 'all':
        projects_qs = projects_qs.filter(status=status_filter)

    if q:
        projects_qs = projects_qs.filter(Q(name__icontains=q) | Q(key__icontains=q) | Q(description__icontains=q))

    # Add task counts per project using SQL aggregation to avoid N+1 queries
    projects_qs = projects_qs.annotate(
        annotated_total_tasks=Count(
            'tasks',
            filter=Q(tasks__archived_at__isnull=True, tasks__parent_task__isnull=True)
        ),
        annotated_done_tasks=Count(
            'tasks',
            filter=Q(tasks__archived_at__isnull=True, tasks__parent_task__isnull=True, tasks__status=TaskStatus.DONE)
        )
    )

    projects_list = []
    for proj in projects_qs:
        total_tasks = proj.annotated_total_tasks
        done_tasks = proj.annotated_done_tasks
        open_tasks = total_tasks - done_tasks
        progress = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else (100 if proj.status == ProjectStatus.COMPLETED else 0)

        projects_list.append({
            'project': proj,
            'total_tasks': total_tasks,
            'done_tasks': done_tasks,
            'open_tasks': open_tasks,
            'progress': progress,
        })

    return render(request, 'projects/list.html', {
        'projects_list': projects_list,
        'show_archived': show_archived,
        'q': q,
        'status_filter': status_filter,
        'status_choices': ProjectStatus.choices,
    })


@login_required
def project_detail_view(request, project_id):
    project = get_object_or_404(Project.objects.select_related('owner', 'workspace'), id=project_id)

    # Filter project tasks
    status = request.GET.get('status', 'all')
    tasks_qs = project.tasks.filter(archived_at__isnull=True, parent_task__isnull=True).select_related('assignee')
    if status != 'all':
        tasks_qs = tasks_qs.filter(status=status)

    milestones = project.milestones.all().order_by('due_date')
    memberships = project.memberships.select_related('user', 'user__profile').all()
    recent_activity = project.activity_events.select_related('actor', 'task').order_by('-created_at')[:10]

    # Task metrics
    total_tasks = project.tasks.filter(archived_at__isnull=True, parent_task__isnull=True).count()
    completed_tasks = project.tasks.filter(archived_at__isnull=True, parent_task__isnull=True, status=TaskStatus.DONE).count()
    progress = int(round((completed_tasks / total_tasks) * 100)) if total_tasks > 0 else 0

    return render(request, 'projects/detail.html', {
        'project': project,
        'tasks': tasks_qs,
        'milestones': milestones,
        'memberships': memberships,
        'recent_activity': recent_activity,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress': progress,
        'current_status': status,
        'task_statuses': TaskStatus.choices,
    })


@require_manager_or_above
def project_create_view(request):
    workspace = getattr(request, 'current_workspace', None) or get_active_workspace(request)
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        key = request.POST.get('key', '').strip().upper()
        description = request.POST.get('description', '').strip()
        owner_id = request.POST.get('owner')
        status = request.POST.get('status', ProjectStatus.ACTIVE)
        color = request.POST.get('color', '#4f46e5')
        start_date = request.POST.get('start_date') or None
        due_date = request.POST.get('due_date') or None

        errors = []
        if not name or not key:
            errors.append("Project name and key are required.")

        if Project.objects.filter(workspace=workspace, key=key).exists():
            errors.append(f"A project with key '{key}' already exists in this workspace.")

        if start_date and due_date and due_date < start_date:
            errors.append("Due date cannot be earlier than start date.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'projects/form.html', {
                'users': users,
                'status_choices': ProjectStatus.choices,
                'action_title': 'Create Project',
            })

        owner = (User.objects.filter(id=owner_id).first() if owner_id else None) or request.user
        project = Project.objects.create(
            workspace=workspace,
            name=name,
            key=key,
            description=description,
            owner=owner,
            status=status,
            color=color,
            start_date=start_date,
            due_date=due_date
        )

        # Add creator / owner to project membership
        ProjectMembership.objects.get_or_create(
            project=project,
            user=owner,
            defaults={'project_role': 'LEAD'}
        )

        record_activity(
            workspace=workspace,
            actor=request.user,
            event_type=ActivityEventType.PROJECT_UPDATED,
            summary=f"{request.user.get_full_name() or request.user.username} created project '{project.name}'",
            project=project
        )

        messages.success(request, f"Project '{project.name}' ({project.key}) created successfully.")
        return redirect('project_detail', project_id=project.id)

    return render(request, 'projects/form.html', {
        'users': users,
        'status_choices': ProjectStatus.choices,
        'action_title': 'Create Project',
    })


@require_manager_or_above
def project_edit_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    workspace = project.workspace
    users = User.objects.filter(workspace_memberships__workspace=workspace).distinct()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        owner_id = request.POST.get('owner')
        status = request.POST.get('status', project.status)
        color = request.POST.get('color', project.color)
        start_date = request.POST.get('start_date') or None
        due_date = request.POST.get('due_date') or None

        if not name:
            messages.error(request, "Project name cannot be empty.")
            return redirect('project_edit', project_id=project.id)

        if start_date and due_date and due_date < start_date:
            messages.error(request, "Due date cannot be earlier than start date.")
            return redirect('project_edit', project_id=project.id)

        project.name = name
        project.description = description
        project.status = status
        project.color = color
        project.start_date = start_date
        project.due_date = due_date
        if owner_id:
            project.owner = User.objects.filter(id=owner_id).first()
        project.save()

        record_activity(
            workspace=workspace,
            actor=request.user,
            event_type=ActivityEventType.PROJECT_UPDATED,
            summary=f"{request.user.get_full_name() or request.user.username} updated project '{project.name}'",
            project=project
        )

        messages.success(request, f"Project '{project.name}' updated successfully.")
        return redirect('project_detail', project_id=project.id)

    return render(request, 'projects/form.html', {
        'project': project,
        'users': users,
        'status_choices': ProjectStatus.choices,
        'action_title': f"Edit Project: {project.name}",
    })


@require_manager_or_above
def project_archive_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        if project.is_archived:
            project.status = ProjectStatus.ACTIVE
            project.archived_at = None
            msg = f"Project '{project.name}' unarchived."
        else:
            project.status = ProjectStatus.ARCHIVED
            project.archived_at = timezone.now()
            msg = f"Project '{project.name}' archived."
        project.save()

        record_activity(
            workspace=project.workspace,
            actor=request.user,
            event_type=ActivityEventType.PROJECT_UPDATED,
            summary=msg,
            project=project
        )

        messages.info(request, msg)
        return redirect('project_list')

    return redirect('project_detail', project_id=project.id)


@require_manager_or_above
def milestone_create_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        due_date = request.POST.get('due_date')
        status = request.POST.get('status', MilestoneStatus.UPCOMING)

        if name and due_date:
            Milestone.objects.create(
                project=project,
                name=name,
                due_date=due_date,
                status=status
            )
            messages.success(request, f"Milestone '{name}' added.")
        else:
            messages.error(request, "Milestone name and due date are required.")

    return redirect('project_detail', project_id=project.id)


@require_manager_or_above
def milestone_toggle_view(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    if request.method == 'POST':
        if milestone.status == MilestoneStatus.ACHIEVED:
            milestone.status = MilestoneStatus.UPCOMING
        else:
            milestone.status = MilestoneStatus.ACHIEVED
        milestone.save()
        messages.success(request, f"Milestone '{milestone.name}' status updated to {milestone.get_status_display()}.")

    return redirect('project_detail', project_id=milestone.project_id)
