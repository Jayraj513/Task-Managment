from django.contrib import admin
from apps.tasks.models import Task, Tag, TaskDependency, Comment, Attachment, TimeEntry


class TaskDependencyInline(admin.TabularInline):
    model = TaskDependency
    fk_name = 'successor_task'
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'title', 'project', 'status', 'priority', 'assignee', 'due_date', 'progress_percent')
    list_filter = ('project', 'status', 'priority', 'assignee')
    search_fields = ('title', 'description')
    inlines = [CommentInline, TimeEntryInline, TaskDependencyInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'color')


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ('predecessor_task', 'successor_task', 'dependency_type', 'created_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'duration_hours', 'entry_date', 'note')
