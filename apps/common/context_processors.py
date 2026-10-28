"""
Global template context processor for Workline.
Supplies workspace context, user roles, active projects, and notification counts.
Optimized to eliminate duplicate database roundtrips.
"""
from apps.workspaces.services import get_active_workspace
from apps.projects.models import Project, ProjectStatus
from apps.notifications.models import Notification
from apps.accounts.permissions import can_manage_workspace, can_manage_projects, can_mutate_tasks


def workline_context(request):
    if not request.user.is_authenticated:
        return {
            'current_workspace': None,
            'active_projects': [],
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'user_profile': None,
            'can_manage_workspace': False,
            'can_manage_projects': False,
            'can_mutate_tasks': False,
        }

    # Retrieve or resolve active workspace safely (memoized on request)
    workspace = get_active_workspace(request)
    request.current_workspace = workspace

    # Active projects for the sidebar navigation (lightweight column projection)
    active_projects = []
    if workspace:
        active_projects = Project.objects.filter(
            workspace=workspace,
            status__in=[ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD]
        ).only('id', 'name', 'color', 'key', 'workspace_id').order_by('name')[:15]

    # Unread notifications count
    unread_count = Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).count()

    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).only('id', 'title', 'message', 'link_url', 'read_at', 'created_at').order_by('-created_at')[:5]

    # In-memory memoize profile on request.user
    user_profile = getattr(request.user, '_cached_profile', None)
    if user_profile is None and hasattr(request.user, 'profile'):
        user_profile = request.user.profile
        request.user._cached_profile = user_profile

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
