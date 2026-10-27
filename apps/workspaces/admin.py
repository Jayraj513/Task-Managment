from django.contrib import admin
from apps.workspaces.models import Workspace, WorkspaceMembership


class WorkspaceMembershipInline(admin.TabularInline):
    model = WorkspaceMembership
    extra = 1


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'timezone', 'created_by', 'created_at')
    search_fields = ('name', 'slug')
    inlines = [WorkspaceMembershipInline]


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'role', 'joined_at')
    list_filter = ('role', 'workspace')
