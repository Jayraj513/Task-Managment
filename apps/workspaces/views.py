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


import os
import time
from django.db import connection
from django.http import JsonResponse


@require_admin
def infra_audit_api(request):
    """
    Secure diagnostic endpoint for administrator to verify production infrastructure:
    Neon pooling status, Neon AWS region, DB ping latency, and Vercel compute region.
    Never exposes passwords, tokens, or usernames.
    """
    db_conf = connection.settings_dict
    host = db_conf.get('HOST', '') or ''
    engine = db_conf.get('ENGINE', '')

    db_ping_ms = None
    try:
        t0 = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        t1 = time.perf_counter()
        db_ping_ms = round((t1 - t0) * 1000, 2)
    except Exception as e:
        db_ping_ms = f"error: {str(e)}"

    is_pooled = '-pooler' in host.lower()
    host_parts = host.split('.')
    neon_region = 'unknown'
    for part in host_parts:
        if part in ['us-east-1', 'us-east-2', 'us-west-2', 'eu-central-1', 'eu-west-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-south-1', 'sa-east-1']:
            neon_region = part
            break

    masked_host = (host[:8] + '...' + host[-15:]) if len(host) > 23 else host

    return JsonResponse({
        'engine': engine.split('.')[-1],
        'is_pooled': is_pooled,
        'neon_region': neon_region,
        'masked_host': masked_host,
        'db_ping_ms': db_ping_ms,
        'vercel_region': os.getenv('VERCEL_REGION', 'iad1'),
    })
