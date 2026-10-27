"""
Workline URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.common.views import root_redirect_view

urlpatterns = [
    path('', root_redirect_view, name='root'),
    path('', include('apps.accounts.urls')),
    path('workspaces/', include('apps.workspaces.urls')),
    path('projects/', include('apps.projects.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = 'apps.common.views.handler403'
handler404 = 'apps.common.views.handler404'
handler500 = 'apps.common.views.handler500'
