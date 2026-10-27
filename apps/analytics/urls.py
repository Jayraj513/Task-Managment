from django.urls import path
from apps.analytics import views

urlpatterns = [
    path('overview/', views.overview_dashboard_view, name='overview'),
    path('workload/', views.team_workload_view, name='team_workload'),
    path('reports/', views.reports_view, name='reports'),
    path('export/csv/', views.export_tasks_csv_view, name='export_tasks_csv'),
]
