from django.urls import path
from apps.accounts import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('admin/users/', views.users_admin_view, name='users_admin'),
]
