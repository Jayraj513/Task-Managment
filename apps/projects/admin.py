from django.contrib import admin
from apps.projects.models import Project, ProjectMembership, Milestone


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'workspace', 'owner', 'status', 'start_date', 'due_date')
    list_filter = ('workspace', 'status')
    search_fields = ('name', 'key')
    inlines = [ProjectMembershipInline, MilestoneInline]


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'due_date', 'status')
    list_filter = ('status', 'project')
