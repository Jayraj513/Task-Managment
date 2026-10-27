from django.contrib import admin
from apps.notifications.models import ActivityEvent, Notification


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'summary', 'actor', 'project', 'task', 'created_at')
    list_filter = ('event_type', 'workspace')
    search_fields = ('summary',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'actor', 'read_at', 'created_at')
    list_filter = ('read_at', 'recipient')
