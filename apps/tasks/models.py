from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.workspaces.models import Workspace
from apps.projects.models import Project


class TaskStatus(models.TextChoices):
    BACKLOG = 'BACKLOG', 'Backlog'
    TODO = 'TODO', 'To Do'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    IN_REVIEW = 'IN_REVIEW', 'In Review'
    BLOCKED = 'BLOCKED', 'Blocked'
    DONE = 'DONE', 'Done'
    CANCELLED = 'CANCELLED', 'Cancelled'


class TaskPriority(models.TextChoices):
    URGENT = 'URGENT', 'Urgent'
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'


class DependencyType(models.TextChoices):
    BLOCKS = 'BLOCKS', 'Blocks'
    RELATES_TO = 'RELATES_TO', 'Relates To'


class Tag(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='reported_tasks'
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimate_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0)],
        help_text='Estimated effort in hours'
    )
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Task completion percentage (0 - 100)'
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
        help_text='Parent task if this is a subtask'
    )
    blocked_reason = models.TextField(
        blank=True,
        default='',
        help_text='Explanation required when task is blocked'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['parent_task']),
            models.Index(fields=['project', 'archived_at', 'parent_task']),
            models.Index(fields=['assignee', 'archived_at']),
            models.Index(fields=['due_date', 'archived_at']),
        ]

    def __str__(self):
        return f"{self.identifier}: {self.title}"

    @property
    def identifier(self):
        return f"{self.project.key}-{self.id}" if self.id else f"{self.project.key}-NEW"

    @property
    def is_archived(self):
        return self.archived_at is not None

    @property
    def is_completed(self):
        return self.status == TaskStatus.DONE

    @property
    def is_cancelled(self):
        return self.status == TaskStatus.CANCELLED

    @property
    def is_blocked(self):
        return self.status == TaskStatus.BLOCKED

    @property
    def is_overdue(self):
        if self.due_date and not (self.is_completed or self.is_cancelled):
            return self.due_date < timezone.localdate()
        return False

    @property
    def logged_hours_total(self):
        if hasattr(self, '_prefetched_objects_cache') and 'time_entries' in self._prefetched_objects_cache:
            return round(sum(float(te.duration_hours or 0.0) for te in self.time_entries.all()), 2)
        result = self.time_entries.aggregate(total=models.Sum('duration_hours'))['total']
        return round(float(result or 0.0), 2)

    @property
    def subtasks_count(self):
        if hasattr(self, '_prefetched_objects_cache') and 'subtasks' in self._prefetched_objects_cache:
            return len([s for s in self.subtasks.all() if not s.archived_at])
        return self.subtasks.filter(archived_at__isnull=True).count()

    @property
    def subtasks_completed_count(self):
        if hasattr(self, '_prefetched_objects_cache') and 'subtasks' in self._prefetched_objects_cache:
            return len([s for s in self.subtasks.all() if not s.archived_at and s.status == TaskStatus.DONE])
        return self.subtasks.filter(archived_at__isnull=True, status=TaskStatus.DONE).count()

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': 'Due date cannot be earlier than start date.'})

        if self.parent_task:
            if self.parent_task_id == self.id:
                raise ValidationError({'parent_task': 'A task cannot be a subtask of itself.'})
            if self.parent_task.parent_task:
                raise ValidationError({'parent_task': 'Subtasks cannot be nested more than one level deep.'})

        if self.status == TaskStatus.BLOCKED and not self.blocked_reason.strip():
            raise ValidationError({'blocked_reason': 'Please specify a reason why this task is blocked.'})

    def save(self, *args, **kwargs):
        # Auto-sync progress percent with status if appropriate
        if self.status == TaskStatus.DONE and self.progress_percent < 100:
            self.progress_percent = 100
        elif self.status == TaskStatus.TODO and self.progress_percent == 100:
            self.progress_percent = 0
        super().save(*args, **kwargs)


class TaskDependency(models.Model):
    predecessor_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='successor_dependencies',
        help_text='The task that must be finished first (or is the dependency prerequisite)'
    )
    successor_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='predecessor_dependencies',
        help_text='The task that depends on the predecessor'
    )
    dependency_type = models.CharField(
        max_length=20,
        choices=DependencyType.choices,
        default=DependencyType.BLOCKS
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('predecessor_task', 'successor_task')
        ordering = ['created_at']
        verbose_name = 'Task Dependency'
        verbose_name_plural = 'Task Dependencies'

    def __str__(self):
        return f"{self.predecessor_task.identifier} -> {self.successor_task.identifier} ({self.dependency_type})"

    def clean(self):
        super().clean()
        if hasattr(self, 'predecessor_task') and hasattr(self, 'successor_task'):
            from apps.tasks.services import validate_dependency
            validate_dependency(
                self.predecessor_task,
                self.successor_task,
                TaskDependency,
                instance_pk=self.pk
            )


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.identifier}"


class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True, default='')
    size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename

    @property
    def formatted_size(self):
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class TimeEntry(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_entries')
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.05)],
        help_text='Logged duration in hours (e.g. 1.5 for 1 hr 30 mins)'
    )
    entry_date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']
        verbose_name = 'Time Entry'
        verbose_name_plural = 'Time Entries'

    def __str__(self):
        return f"{self.user.username} logged {self.duration_hours}h on {self.task.identifier}"
