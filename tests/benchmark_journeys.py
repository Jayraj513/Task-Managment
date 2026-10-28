"""
Performance benchmark harness for representative user journeys in OGFLOW.
Measures SQL query count, DB time, and total server execution time.
"""
import time
import django
from django.db import connection, reset_queries
from django.test import Client
from django.contrib.auth.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.projects.models import Project, ProjectStatus
from apps.tasks.models import Task, TaskStatus, TaskPriority
from apps.accounts.models import Role


def run_benchmarks():
    client = Client()
    
    # Ensure test user and data exist
    user, _ = User.objects.get_or_create(username='benchmark_admin', defaults={'is_superuser': True, 'email': 'bench@example.com'})
    user.set_password('Password123!')
    user.save()
    if hasattr(user, 'profile'):
        user.profile.role = Role.ADMIN
        user.profile.save()

    ws = Workspace.objects.first()
    if not ws:
        ws = Workspace.objects.create(name='Benchmark WS', slug='benchmark-ws', created_by=user)
    WorkspaceMembership.objects.get_or_create(workspace=ws, user=user, defaults={'role': Role.ADMIN})

    # Ensure at least 3 projects and 20 tasks exist for realistic measurement
    projects = list(Project.objects.filter(workspace=ws))
    if len(projects) < 3:
        for i in range(len(projects), 3):
            p = Project.objects.create(workspace=ws, name=f'Benchmark Project {i+1}', key=f'BP{i+1}', owner=user)
            projects.append(p)

    tasks_count = Task.objects.filter(project__workspace=ws).count()
    if tasks_count < 20:
        for i in range(tasks_count, 20):
            p = projects[i % len(projects)]
            Task.objects.create(
                project=p,
                title=f'Benchmark Task {i+1}',
                reporter=user,
                assignee=user if i % 2 == 0 else None,
                status=TaskStatus.DONE if i % 4 == 0 else TaskStatus.TODO,
                priority=TaskPriority.HIGH if i % 3 == 0 else TaskPriority.MEDIUM,
            )

    client.login(username='benchmark_admin', password='Password123!')

    from django.urls import reverse

    test_journeys = [
        ('1. Overview Dashboard', reverse('overview')),
        ('2. Projects List', reverse('project_list')),
        ('3. Project Detail', reverse('project_detail', args=[projects[0].id])),
        ('4. Task Board (Kanban)', reverse('task_board')),
        ('5. Task List (Table)', reverse('task_list')),
        ('6. My Tasks', reverse('my_tasks')),
        ('7. Task Calendar', reverse('task_calendar')),
        ('8. Gantt Timeline', reverse('task_gantt')),
        ('9. Team Workload', reverse('team_workload')),
        ('10. Executive Reports', reverse('reports')),
        ('11. Notifications', reverse('notification_list')),
        ('12. Workspace Settings', reverse('workspace_settings')),
    ]

    print(f"{'Journey / View':<28} | {'Queries':<8} | {'Time (ms)':<10}")
    print("-" * 52)

    django.conf.settings.DEBUG = True

    for name, url in test_journeys:
        reset_queries()
        t0 = time.perf_counter()
        resp = client.get(url)
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000
        queries_count = len(connection.queries)
        status = resp.status_code
        print(f"{name:<28} | {queries_count:<8} | {elapsed_ms:>8.2f} ms (HTTP {status})")

    django.conf.settings.DEBUG = False


if __name__ == '__main__':
    run_benchmarks()

def inspect_queries(url):
    client = Client()
    client.login(username='benchmark_admin', password='Password123!')
    django.conf.settings.DEBUG = True
    reset_queries()
    resp = client.get(url)
    print(f"\n--- Queries for {url} (Total: {len(connection.queries)}) ---")
    for i, q in enumerate(connection.queries):
        print(f"{i+1}. {q['time']}s | {q['sql']}")
    django.conf.settings.DEBUG = False
