from django.urls import path
from apps.tasks import views

urlpatterns = [
    # Main Navigation Views
    path('board/', views.task_board_view, name='task_board'),
    path('list/', views.task_list_view, name='task_list'),
    path('my-tasks/', views.my_tasks_view, name='my_tasks'),
    path('calendar/', views.task_calendar_view, name='task_calendar'),
    path('gantt/', views.task_gantt_view, name='task_gantt'),

    # Task CRUD
    path('new/', views.task_create_view, name='task_create'),
    path('quick-create/', views.task_quick_create_api, name='task_quick_create'),
    path('<int:task_id>/', views.task_detail_view, name='task_detail'),
    path('<int:task_id>/edit/', views.task_edit_view, name='task_edit'),
    path('<int:task_id>/archive/', views.task_archive_view, name='task_archive'),

    # Interactive APIs & Sub-actions
    path('api/<int:task_id>/status/', views.api_update_task_status, name='api_update_task_status'),
    path('<int:task_id>/comments/add/', views.task_add_comment, name='task_add_comment'),
    path('<int:task_id>/time/add/', views.task_add_time_entry, name='task_add_time_entry'),
    path('<int:task_id>/attachments/add/', views.task_add_attachment, name='task_add_attachment'),
    path('<int:task_id>/dependencies/add/', views.task_add_dependency, name='task_add_dependency'),
    path('dependencies/<int:dependency_id>/delete/', views.task_delete_dependency, name='task_delete_dependency'),
]
