from django.urls import path
from apps.projects import views

urlpatterns = [
    path('', views.project_list_view, name='project_list'),
    path('new/', views.project_create_view, name='project_create'),
    path('<int:project_id>/', views.project_detail_view, name='project_detail'),
    path('<int:project_id>/edit/', views.project_edit_view, name='project_edit'),
    path('<int:project_id>/archive/', views.project_archive_view, name='project_archive'),
    path('<int:project_id>/milestones/new/', views.milestone_create_view, name='milestone_create'),
    path('milestones/<int:milestone_id>/toggle/', views.milestone_toggle_view, name='milestone_toggle'),
]
