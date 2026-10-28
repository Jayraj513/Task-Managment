"""
Regression and performance tests for Workspace resolution, Project creation, and Analytics.
"""
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from apps.accounts.models import Role, UserProfile
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.services import get_active_workspace
from apps.projects.models import Project, ProjectStatus
from apps.tasks.models import Task, TaskStatus, TaskPriority
from apps.analytics.services import calculate_dashboard_kpis, get_completion_trend, get_assignee_distribution
from apps.accounts.views import csrf_failure_view


class WorkspaceAndProjectTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_user',
            email='admin@example.com',
            password='Password123!'
        )
        self.admin.profile.role = Role.ADMIN
        self.admin.profile.save()

    def test_get_active_workspace_auto_initialization(self):
        """When 0 workspaces exist, get_active_workspace creates a valid default workspace."""
        self.assertEqual(Workspace.objects.count(), 0)

        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin
        request.session = {}

        ws = get_active_workspace(request)
        self.assertIsNotNone(ws)
        self.assertEqual(Workspace.objects.count(), 1)
        self.assertEqual(ws.slug, 'acme-workspace')
        self.assertTrue(WorkspaceMembership.objects.filter(workspace=ws, user=self.admin, role=Role.ADMIN).exists())

    def test_project_create_view_with_no_preexisting_workspace(self):
        """Creating a project when 0 workspaces exist must succeed without HTTP 500 error."""
        self.assertEqual(Workspace.objects.count(), 0)
        self.client.login(username='admin_user', password='Password123!')

        response = self.client.post(reverse('project_create'), {
            'name': 'Alpha Launch',
            'key': 'ALPHA',
            'description': 'Main product roadmap launch',
            'status': ProjectStatus.ACTIVE,
            'color': '#4f46e5',
        })

        # Must redirect to project detail (HTTP 302), NOT 500
        self.assertEqual(response.status_code, 302)
        project = Project.objects.filter(key='ALPHA').first()
        self.assertIsNotNone(project)
        self.assertEqual(project.name, 'Alpha Launch')
        self.assertIsNotNone(project.workspace)
        self.assertEqual(project.owner, self.admin)

    def test_project_list_view_query_efficiency(self):
        """Project list view must not suffer from N+1 task counting queries."""
        ws = Workspace.objects.create(name='Test WS', slug='test-ws', created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=ws, user=self.admin, role=Role.ADMIN)

        # Create 10 projects each with 3 tasks
        for i in range(10):
            proj = Project.objects.create(
                workspace=ws,
                name=f'Project {i}',
                key=f'P{i}',
                owner=self.admin
            )
            for j in range(3):
                Task.objects.create(
                    project=proj,
                    title=f'Task {i}-{j}',
                    reporter=self.admin,
                    status=TaskStatus.DONE if j == 0 else TaskStatus.TODO
                )

        self.client.login(username='admin_user', password='Password123!')

        # With SQL annotation, the query count is constant (13 queries total)
        # and does NOT scale with the number of projects (which would be 10*2 = 20 extra queries without annotation).
        with self.assertNumQueries(13):
            response = self.client.get(reverse('project_list'))
            self.assertEqual(response.status_code, 200)

    def test_calculate_dashboard_kpis_single_query(self):
        """calculate_dashboard_kpis must compute all 8 KPI metrics in exactly 1 SQL query."""
        ws = Workspace.objects.create(name='Analytics WS', slug='analytics-ws', created_by=self.admin)
        proj = Project.objects.create(workspace=ws, name='Analytics Proj', key='AP', owner=self.admin)

        for i in range(10):
            Task.objects.create(
                project=proj,
                title=f'Metric Task {i}',
                reporter=self.admin,
                status=TaskStatus.DONE if i < 3 else TaskStatus.TODO
            )

        qs = Task.objects.filter(project__workspace=ws)

        with self.assertNumQueries(1):
            kpis = calculate_dashboard_kpis(qs)

        self.assertEqual(kpis['total_tasks'], 10)
        self.assertEqual(kpis['completed_total'], 3)
        self.assertEqual(kpis['total_open'], 7)

    def test_completion_trend_two_queries(self):
        """get_completion_trend must use exactly 2 queries instead of 28 loop queries."""
        ws = Workspace.objects.create(name='Trend WS', slug='trend-ws', created_by=self.admin)
        proj = Project.objects.create(workspace=ws, name='Trend Proj', key='TP', owner=self.admin)
        Task.objects.create(project=proj, title='Trend Task', reporter=self.admin)

        qs = Task.objects.filter(project__workspace=ws)
        with self.assertNumQueries(2):
            trend = get_completion_trend(qs, days=14)

        self.assertEqual(len(trend['labels']), 14)
        self.assertEqual(len(trend['created_counts']), 14)
        self.assertEqual(len(trend['completed_counts']), 14)

    def test_assignee_distribution_query_efficiency(self):
        """get_assignee_distribution must use exactly 3 queries (users + open + done) regardless of user count."""
        ws = Workspace.objects.create(name='Assignee WS', slug='assignee-ws', created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=ws, user=self.admin, role=Role.ADMIN)

        # Add 3 more users
        for i in range(3):
            u = User.objects.create_user(username=f'user_{i}', password='Password123!')
            WorkspaceMembership.objects.create(workspace=ws, user=u, role=Role.MEMBER)

        proj = Project.objects.create(workspace=ws, name='Assignee Proj', key='ASP', owner=self.admin)
        Task.objects.create(project=proj, title='Assigned Task', reporter=self.admin, assignee=self.admin)

        qs = Task.objects.filter(project__workspace=ws)
        with self.assertNumQueries(3):
            dist = get_assignee_distribution(ws, qs)

        self.assertIn(self.admin.username, dist['labels'][0])

    def test_csrf_failure_view_graceful_redirect(self):
        """csrf_failure_view gracefully redirects without crashing even if messages middleware is unavailable."""
        factory = RequestFactory()
        request = factory.post('/login/')
        # Do not attach _messages
        response = csrf_failure_view(request, reason="CSRF token missing or incorrect.")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
