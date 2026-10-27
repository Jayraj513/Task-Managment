from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from apps.accounts.models import Role


class Workspace(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True, default='')
    timezone = models.CharField(max_length=60, default='UTC')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_workspaces'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'workspace'
            slug = base_slug
            counter = 1
            while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class WorkspaceMembership(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')
        ordering = ['joined_at']
        verbose_name = 'Workspace Membership'
        verbose_name_plural = 'Workspace Memberships'

    def __str__(self):
        return f"{self.user.username} in {self.workspace.name} ({self.role})"
