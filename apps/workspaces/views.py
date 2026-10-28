from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.workspaces.models import Workspace
from apps.workspaces.services import get_active_workspace
from apps.accounts.permissions import require_admin
from django.core.management import call_command


@require_admin
def workspace_settings_view(request):
    workspace = getattr(request, 'current_workspace', None) or get_active_workspace(request)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_settings':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            tz_val = request.POST.get('timezone', 'UTC').strip()

            if name:
                workspace.name = name
                workspace.description = description
                workspace.timezone = tz_val
                workspace.save()
                messages.success(request, "Workspace settings saved.")
            else:
                messages.error(request, "Workspace name cannot be empty.")
            return redirect('workspace_settings')

        elif action == 'seed_demo':
            try:
                call_command('seed_demo')
                messages.success(request, "Demo data successfully re-seeded and refreshed!")
            except Exception as e:
                messages.error(request, f"Seeding error: {str(e)}")
            return redirect('overview')

    return render(request, 'accounts/workspace_settings.html', {
        'workspace': workspace,
    })
