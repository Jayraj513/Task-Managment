from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.workspaces.models import Workspace
from apps.projects.models import Project
from apps.tasks.models import Task, TaskDependency, DependencyType
from apps.tasks.services import validate_dependency, detect_dependency_cycle


class DependencyCycleValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dep_tester', password='TestPassword123!')
        self.workspace = Workspace.objects.create(name='Dep WS', slug='dep-ws')
        self.project = Project.objects.create(
            workspace=self.workspace,
            name='Dep Project',
            key='DEP',
            owner=self.user
        )
        self.task_a = Task.objects.create(project=self.project, title='Task A', reporter=self.user)
        self.task_b = Task.objects.create(project=self.project, title='Task B', reporter=self.user)
        self.task_c = Task.objects.create(project=self.project, title='Task C', reporter=self.user)
        self.task_d = Task.objects.create(project=self.project, title='Task D', reporter=self.user)

    def test_self_dependency_rejected(self):
        """A task cannot depend on itself."""
        with self.assertRaises(ValidationError):
            validate_dependency(self.task_a, self.task_a, TaskDependency)

    def test_valid_linear_dependency(self):
        """A -> B and B -> C linear chain is valid."""
        TaskDependency.objects.create(predecessor_task=self.task_a, successor_task=self.task_b)
        TaskDependency.objects.create(predecessor_task=self.task_b, successor_task=self.task_c)
        self.assertFalse(detect_dependency_cycle(self.task_c.id, self.task_d.id, TaskDependency))

    def test_direct_inverse_dependency_rejected(self):
        """If A -> B, then creating B -> A must be rejected as a cycle."""
        TaskDependency.objects.create(predecessor_task=self.task_a, successor_task=self.task_b)
        with self.assertRaises(ValidationError):
            validate_dependency(self.task_b, self.task_a, TaskDependency)

    def test_multi_node_cycle_rejected(self):
        """If A -> B -> C, then creating C -> A must be detected as a circular loop."""
        TaskDependency.objects.create(predecessor_task=self.task_a, successor_task=self.task_b)
        TaskDependency.objects.create(predecessor_task=self.task_b, successor_task=self.task_c)

        # C -> A should be detected as a cycle!
        is_cycle = detect_dependency_cycle(self.task_c.id, self.task_a.id, TaskDependency)
        self.assertTrue(is_cycle)

        with self.assertRaises(ValidationError):
            validate_dependency(self.task_c, self.task_a, TaskDependency)
