"""
Global template context processor for Workline.
Supplies workspace context, user roles, active projects, and notification counts.
"""
from apps.workspaces.models import Workspace
from apps.projects.models import Project, ProjectStatus
from apps.notifications.models import Notification
from apps.accounts.permissions import can_manage_workspace, can_manage_projects, can_mutate_tasks


def workline_context(request):
    if not request.user.is_authenticated:
        return {
            'current_workspace': None,
            'active_projects': [],
            'unread_notifications_count': 0,
            'can_manage_workspace': False,
            'can_manage_projects': False,
            'can_mutate_tasks': False,
        }

    # Retrieve or select default workspace
    workspace = None
    workspace_id = request.session.get('active_workspace_id')
    if workspace_id:
        workspace = Workspace.objects.filter(id=workspace_id).first()

    if not workspace:
        # Fallback to first workspace user belongs to or first available
        membership = request.user.workspace_memberships.select_related('workspace').first()
        if membership:
            workspace = membership.workspace
        else:
            workspace = Workspace.objects.first()

        if workspace:
            request.session['active_workspace_id'] = workspace.id

    # Active projects for the sidebar navigation
    active_projects = []
    if workspace:
        active_projects = Project.objects.filter(
            workspace=workspace,
            status__in=[ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD]
        ).order_by('name')[:15]

    # Unread notifications count
    unread_count = Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).count()

    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]

    user_profile = getattr(request.user, 'profile', None)

    return {
        'current_workspace': workspace,
        'active_projects': active_projects,
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'user_profile': user_profile,
        'can_manage_workspace': can_manage_workspace(request.user),
        'can_manage_projects': can_manage_projects(request.user),
        'can_mutate_tasks': can_mutate_tasks(request.user),
    }
