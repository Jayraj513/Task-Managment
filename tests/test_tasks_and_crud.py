from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.workspaces.models import Workspace
from apps.projects.models import Project, ProjectStatus
from apps.tasks.models import Task, TaskStatus, TaskPriority, Comment, TimeEntry


class TaskCRUDAndValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='TestPassword123!')
        self.workspace = Workspace.objects.create(name='Test Workspace', slug='test-workspace', created_by=self.user)
        self.project = Project.objects.create(
            workspace=self.workspace,
            name='Test Project',
            key='TST',
            owner=self.user,
            status=ProjectStatus.ACTIVE
        )

    def test_task_creation_valid(self):
        """Valid task creation succeeds with defaults."""
        task = Task.objects.create(
            project=self.project,
            title='Sample Task',
            reporter=self.user,
            assignee=self.user,
            estimate_hours=Decimal('4.5')
        )
        self.assertEqual(task.identifier, f"TST-{task.id}")
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertFalse(task.is_overdue)

    def test_invalid_date_range_rejected(self):
        """Due date earlier than start date must raise ValidationError."""
        today = timezone.localdate()
        task = Task(
            project=self.project,
            title='Invalid Date Task',
            reporter=self.user,
            start_date=today,
            due_date=today - timedelta(days=2) # earlier than start!
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_blocked_task_requires_reason(self):
        """Setting status to BLOCKED without blocked_reason must raise ValidationError."""
        task = Task(
            project=self.project,
            title='Blocked Task',
            reporter=self.user,
            status=TaskStatus.BLOCKED,
            blocked_reason='' # Empty!
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_status_done_sets_progress_100(self):
        """Moving task to DONE automatically sets progress_percent to 100."""
        task = Task.objects.create(
            project=self.project,
            title='Task Done Auto Progress',
            reporter=self.user,
            status=TaskStatus.TODO,
            progress_percent=25
        )
        task.status = TaskStatus.DONE
        task.save()
        self.assertEqual(task.progress_percent, 100)

    def test_subtask_and_parent_relationship(self):
        """Subtask points to parent and self-reference subtask is blocked."""
        parent = Task.objects.create(
            project=self.project,
            title='Parent Task',
            reporter=self.user
        )
        sub = Task.objects.create(
            project=self.project,
            title='Child Subtask',
            reporter=self.user,
            parent_task=parent
        )
        self.assertEqual(parent.subtasks.count(), 1)
        self.assertEqual(parent.subtasks.first(), sub)

        # Self-parenting check
        parent.parent_task = parent
        with self.assertRaises(ValidationError):
            parent.full_clean()

    def test_time_entry_aggregation(self):
        """Time entries aggregate correctly on task."""
        task = Task.objects.create(project=self.project, title='Timed Task', reporter=self.user)
        TimeEntry.objects.create(task=task, user=self.user, duration_hours=Decimal('2.5'), note='Work 1')
        TimeEntry.objects.create(task=task, user=self.user, duration_hours=Decimal('1.5'), note='Work 2')
        self.assertEqual(task.logged_hours_total, 4.0)
