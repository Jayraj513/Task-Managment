from django.db import models
from django.contrib.auth.models import User
from apps.workspaces.models import Workspace
from apps.projects.models import Project
from apps.tasks.models import Task


class ActivityEventType(models.TextChoices):
    TASK_CREATED = 'TASK_CREATED', 'Task Created'
    STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
    PRIORITY_CHANGED = 'PRIORITY_CHANGED', 'Priority Changed'
    ASSIGNED = 'ASSIGNED', 'Assignee Changed'
    COMMENTED = 'COMMENTED', 'Comment Added'
    TIME_LOGGED = 'TIME_LOGGED', 'Time Logged'
    DATES_CHANGED = 'DATES_CHANGED', 'Dates Changed'
    DEPENDENCY_ADDED = 'DEPENDENCY_ADDED', 'Dependency Added'
    PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project Updated'


class ActivityEvent(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='activity_events')
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_events'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_events'
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_events'
    )
    event_type = models.CharField(max_length=40, choices=ActivityEventType.choices)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['workspace', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.summary}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications'
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    event_type = models.CharField(max_length=50, default='SYSTEM')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_url = models.CharField(max_length=255, blank=True, default='')
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"

    @property
    def is_read(self):
        return self.read_at is not None
