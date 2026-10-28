from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.workspaces.models import Workspace


class ProjectStatus(models.TextChoices):
    PLANNING = 'PLANNING', 'Planning'
    ACTIVE = 'ACTIVE', 'Active'
    ON_HOLD = 'ON_HOLD', 'On Hold'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'


class MilestoneStatus(models.TextChoices):
    UPCOMING = 'UPCOMING', 'Upcoming'
    ACHIEVED = 'ACHIEVED', 'Achieved'
    DELAYED = 'DELAYED', 'Delayed'


class Project(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=150)
    key = models.CharField(max_length=12, help_text='Short uppercase project prefix (e.g. CORE, MKTG)')
    description = models.TextField(blank=True, default='')
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_projects'
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE
    )
    color = models.CharField(max_length=20, default='#4f46e5')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workspace', 'key')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['workspace', 'archived_at']),
        ]

    def __str__(self):
        return f"[{self.key}] {self.name}"

    def clean(self):
        super().clean()
        if self.key:
            self.key = self.key.strip().upper()
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': 'Project due date cannot be earlier than start date.'})

    def save(self, *args, **kwargs):
        if self.key:
            self.key = self.key.strip().upper()
        if self.status == ProjectStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        elif self.status != ProjectStatus.ARCHIVED and self.archived_at:
            self.archived_at = None
        super().save(*args, **kwargs)

    @property
    def is_archived(self):
        return self.status == ProjectStatus.ARCHIVED or self.archived_at is not None

    @property
    def total_tasks_count(self):
        return self.tasks.filter(archived_at__isnull=True, parent_task__isnull=True).count()

    @property
    def completed_tasks_count(self):
        return self.tasks.filter(
            archived_at__isnull=True,
            parent_task__isnull=True,
            status='DONE'
        ).count()

    @property
    def progress_percent(self):
        total = self.total_tasks_count
        if total == 0:
            return 100 if self.status == ProjectStatus.COMPLETED else 0
        completed = self.completed_tasks_count
        return int(round((completed / total) * 100))


class ProjectMembership(models.Model):
    ROLE_CHOICES = [
        ('LEAD', 'Project Lead'),
        ('CONTRIBUTOR', 'Contributor'),
        ('VIEWER', 'Viewer'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    project_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CONTRIBUTOR')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.project.key} as {self.project_role}"


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=MilestoneStatus.choices,
        default=MilestoneStatus.UPCOMING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.project.key} Milestone: {self.name} ({self.due_date})"
