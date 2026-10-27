from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin (Full Workspace Access)'
    MANAGER = 'MANAGER', 'Manager (Projects & Team Tasks)'
    MEMBER = 'MEMBER', 'Member (Assigned Work & Comments)'
    VIEWER = 'VIEWER', 'Viewer (Read-only Access)'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    job_title = models.CharField(max_length=120, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    weekly_capacity_hours = models.PositiveIntegerField(
        default=40,
        help_text='Configurable weekly working capacity in hours for workload estimation'
    )
    avatar_color = models.CharField(max_length=20, default='#4f46e5')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name', 'user__username']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        full_name = self.user.get_full_name()
        return f"{full_name or self.user.username} ({self.get_role_display()})"

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full if full else self.user.username

    @property
    def initials(self):
        first = self.user.first_name[:1] if self.user.first_name else ''
        last = self.user.last_name[:1] if self.user.last_name else ''
        if first or last:
            return f"{first}{last}".upper()
        return self.user.username[:2].upper()

    @property
    def is_admin(self):
        return self.user.is_superuser or self.role == Role.ADMIN

    @property
    def is_manager(self):
        return self.is_admin or self.role == Role.MANAGER

    @property
    def can_manage_projects(self):
        return self.is_manager

    @property
    def can_edit_tasks(self):
        return self.role in (Role.ADMIN, Role.MANAGER, Role.MEMBER) or self.user.is_superuser

    @property
    def is_viewer(self):
        return self.role == Role.VIEWER and not self.user.is_superuser


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Ensure UserProfile always exists for every User."""
    if kwargs.get('raw', False):
        return
    if created:
        role = Role.ADMIN if instance.is_superuser else Role.MEMBER
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance, role=Role.ADMIN if instance.is_superuser else Role.MEMBER)
