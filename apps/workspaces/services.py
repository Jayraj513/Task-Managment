"""
Workspace services and active workspace resolution for Workline / OGFLOW.
"""
from django.db import IntegrityError
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.accounts.models import Role
from django.contrib.auth.models import User


def get_active_workspace(request=None):
    """
    Resolves the active Workspace for the request in order of preference:
    1. Session 'active_workspace_id'.
    2. User's workspace membership.
    3. First existing Workspace in the database.
    4. Auto-creates a default workspace if none exists, preventing null foreign key
       violations and 500 errors across projects, tasks, and analytics.
    Also ensures the authenticated user has an active WorkspaceMembership record.
    """
    workspace = None

    if request and hasattr(request, 'session'):
        ws_id = request.session.get('active_workspace_id')
        if ws_id:
            workspace = Workspace.objects.filter(id=ws_id).first()

    if not workspace and request and hasattr(request, 'user') and request.user.is_authenticated:
        membership = request.user.workspace_memberships.select_related('workspace').first()
        if membership:
            workspace = membership.workspace

    if not workspace:
        workspace = Workspace.objects.first()

    # If no workspace exists in the database, safely initialize default workspace
    if not workspace:
        creator = None
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            creator = request.user
        else:
            creator = User.objects.filter(is_superuser=True).first()

        try:
            workspace, _ = Workspace.objects.get_or_create(
                slug="acme-workspace",
                defaults={
                    'name': "Acme Workspace",
                    'description': "Primary organization workspace",
                    'created_by': creator,
                }
            )
        except IntegrityError:
            workspace = Workspace.objects.first()

        if workspace and creator:
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=creator,
                defaults={'role': Role.ADMIN}
            )

    # Ensure authenticated user has a membership in this active workspace
    if request and hasattr(request, 'user') and request.user.is_authenticated and workspace:
        if not WorkspaceMembership.objects.filter(workspace=workspace, user=request.user).exists():
            user_role = Role.ADMIN if (request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'is_admin', False)) else Role.MEMBER
            try:
                WorkspaceMembership.objects.get_or_create(
                    workspace=workspace,
                    user=request.user,
                    defaults={'role': user_role}
                )
            except IntegrityError:
                pass

    if request and hasattr(request, 'session') and workspace:
        request.session['active_workspace_id'] = workspace.id

    if request:
        request.current_workspace = workspace

    return workspace
