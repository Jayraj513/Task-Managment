"""
Role-based access control and permission enforcement.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from apps.accounts.models import Role


def get_user_role(user):
    """Retrieve the primary role for the authenticated user."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return Role.ADMIN
    if hasattr(user, 'profile'):
        return user.profile.role
    return Role.MEMBER


def can_manage_workspace(user):
    """Admin role or superuser only."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin)


def can_manage_projects(user):
    """Admin or Manager role."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.is_manager)


def can_mutate_tasks(user):
    """Admin, Manager, or Member role (Viewers cannot mutate)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.role in (Role.ADMIN, Role.MANAGER, Role.MEMBER)
    return False


def can_edit_task(user, task):
    """Check if a specific user can edit a specific task."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.is_manager):
        return True
    if hasattr(user, 'profile') and user.profile.role == Role.MEMBER:
        # Members can update assigned tasks or tasks where they are reporter
        return task.assignee_id == user.id or task.reporter_id == user.id or task.project.owner_id == user.id
    return False


def require_admin(view_func):
    """Decorator to require Admin role."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not can_manage_workspace(request.user):
            raise PermissionDenied("You do not have permission to access Workspace Administration.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_manager_or_above(view_func):
    """Decorator to require Manager or Admin role."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not can_manage_projects(request.user):
            raise PermissionDenied("Manager or Admin access required for this action.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_mutation_allowed(view_func):
    """Decorator to block Viewer role from modifying data."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not can_mutate_tasks(request.user):
            raise PermissionDenied("Viewer accounts have read-only access.")
        return view_func(request, *args, **kwargs)
    return _wrapped
