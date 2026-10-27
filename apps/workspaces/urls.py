from django.urls import path
from apps.workspaces import views

urlpatterns = [
    path('settings/', views.workspace_settings_view, name='workspace_settings'),
]
