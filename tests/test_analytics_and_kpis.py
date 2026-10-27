from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.workspaces.models import Workspace
from apps.projects.models import Project, ProjectStatus
from apps.tasks.models import Task, TaskStatus, TaskPriority
from apps.analytics.services import (
    calculate_dashboard_kpis,
    get_filtered_tasks_queryset,
    get_team_workload_matrix
)


class AnalyticsAndKPITests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.user_a = User.objects.create_user(username='dev_a', password='TestPassword123!')
        self.user_b = User.objects.create_user(username='dev_b', password='TestPassword123!')
        self.workspace = Workspace.objects.create(name='KPI WS', slug='kpi-ws')

        self.project_1 = Project.objects.create(workspace=self.workspace, name='P1', key='P1', owner=self.user_a)
        self.project_2 = Project.objects.create(workspace=self.workspace, name='P2', key='P2', owner=self.user_b)

        # 1. Open task (in progress)
        Task.objects.create(
            project=self.project_1, title='T1 Open', status=TaskStatus.IN_PROGRESS,
            assignee=self.user_a, reporter=self.user_a, due_date=today + timedelta(days=5),
            estimate_hours=Decimal('10.0')
        )
        # 2. Overdue task (open)
        Task.objects.create(
            project=self.project_1, title='T2 Overdue', status=TaskStatus.TODO,
            assignee=self.user_a, reporter=self.user_a, due_date=today - timedelta(days=3),
            estimate_hours=Decimal('5.0')
        )
        # 3. Blocked task
        Task.objects.create(
            project=self.project_1, title='T3 Blocked', status=TaskStatus.BLOCKED,
            blocked_reason='Waiting on server', assignee=self.user_b, reporter=self.user_a,
            due_date=today + timedelta(days=2), estimate_hours=Decimal('8.0')
        )
        # 4. Completed task (due date was in past, but status is DONE so NOT overdue)
        Task.objects.create(
            project=self.project_2, title='T4 Done Past', status=TaskStatus.DONE,
            assignee=self.user_b, reporter=self.user_b, due_date=today - timedelta(days=4),
            estimate_hours=Decimal('12.0'), progress_percent=100
        )
        # 5. Cancelled task
        Task.objects.create(
            project=self.project_2, title='T5 Cancelled', status=TaskStatus.CANCELLED,
            assignee=self.user_b, reporter=self.user_b, due_date=today - timedelta(days=2),
            estimate_hours=Decimal('2.0')
        )
        # 6. Unassigned open task
        Task.objects.create(
            project=self.project_2, title='T6 Unassigned', status=TaskStatus.TODO,
            assignee=None, reporter=self.user_a, due_date=today + timedelta(days=1),
            estimate_hours=Decimal('4.0')
        )

    def test_kpi_totals_match_expected(self):
        """KPI totals accurately reflect the test database state."""
        qs = Task.objects.filter(project__workspace=self.workspace, archived_at__isnull=True, parent_task__isnull=True)
        kpis = calculate_dashboard_kpis(qs)

        self.assertEqual(kpis['total_tasks'], 6)
        # Open tasks exclude DONE and CANCELLED: T1, T2, T3, T6 => 4
        self.assertEqual(kpis['total_open'], 4)
        # Overdue task is only T2 (T4 is DONE and T5 is CANCELLED)
        self.assertEqual(kpis['overdue_count'], 1)
        # Blocked task is T3
        self.assertEqual(kpis['blocked_count'], 1)
        # Unassigned open task is T6
        self.assertEqual(kpis['unassigned_count'], 1)
        # Total completed is T4 => 1
        self.assertEqual(kpis['completed_total'], 1)

    def test_zero_division_safety(self):
        """Empty queryset does not raise ZeroDivisionError."""
        empty_qs = Task.objects.none()
        kpis = calculate_dashboard_kpis(empty_qs)
        self.assertEqual(kpis['completion_rate'], 0)
        self.assertEqual(kpis['total_tasks'], 0)

    def test_filtered_tasks_queryset(self):
        """Query params accurately filter tasks."""
        # Filter by project 1
        p1_tasks = get_filtered_tasks_queryset(self.workspace, {'project': str(self.project_1.id)})
        self.assertEqual(p1_tasks.count(), 3)

        # Filter by assignee user_a
        ua_tasks = get_filtered_tasks_queryset(self.workspace, {'assignee': str(self.user_a.id)})
        self.assertEqual(ua_tasks.count(), 2)

        # Filter by unassigned
        unassigned = get_filtered_tasks_queryset(self.workspace, {'assignee': 'unassigned'})
        self.assertEqual(unassigned.count(), 1)
        self.assertEqual(unassigned.first().title, 'T6 Unassigned')
