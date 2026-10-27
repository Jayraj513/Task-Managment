from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.accounts.models import Role, UserProfile
from apps.workspaces.models import Workspace, WorkspaceMembership


class AuthAndRolePermissionTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_user(username='admin_test', password='TestPassword123!')
        self.admin.profile.role = Role.ADMIN
        self.admin.profile.save()

        # Manager user
        self.manager = User.objects.create_user(username='manager_test', password='TestPassword123!')
        self.manager.profile.role = Role.MANAGER
        self.manager.profile.save()

        # Member user
        self.member = User.objects.create_user(username='member_test', password='TestPassword123!')
        self.member.profile.role = Role.MEMBER
        self.member.profile.save()

        # Viewer user
        self.viewer = User.objects.create_user(username='viewer_test', password='TestPassword123!')
        self.viewer.profile.role = Role.VIEWER
        self.viewer.profile.save()

        # Workspace
        self.workspace = Workspace.objects.create(name='Test WS', slug='test-ws')
        for u in [self.admin, self.manager, self.member, self.viewer]:
            WorkspaceMembership.objects.create(workspace=self.workspace, user=u, role=u.profile.role)

    def test_anonymous_redirected_to_login(self):
        """Anonymous requests to private views should redirect to login."""
        response = self.client.get(reverse('overview'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_anonymous_root_redirects_to_login(self):
        """Logged-out visitors accessing the root URL '/' should redirect directly to login."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

    def test_authenticated_root_redirects_to_overview(self):
        """Authenticated users accessing the root URL '/' should redirect to overview."""
        self.client.login(username='admin_test', password='TestPassword123!')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('overview'))

    def test_login_and_logout(self):
        """User can log in and log out."""
        login_success = self.client.login(username='admin_test', password='TestPassword123!')
        self.assertTrue(login_success)

        response = self.client.get(reverse('overview'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_member_blocked_from_admin_endpoints(self):
        """Members cannot access admin-only endpoints."""
        self.client.login(username='member_test', password='TestPassword123!')
        response = self.client.get(reverse('users_admin'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse('workspace_settings'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_endpoints(self):
        """Admins can access workspace admin endpoints."""
        self.client.login(username='admin_test', password='TestPassword123!')
        response = self.client.get(reverse('users_admin'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('workspace_settings'))
        self.assertEqual(response.status_code, 200)

    def test_viewer_blocked_from_task_creation(self):
        """Viewers have read-only access and cannot create tasks."""
        self.client.login(username='viewer_test', password='TestPassword123!')
        response = self.client.get(reverse('task_create'))
        self.assertEqual(response.status_code, 403)
