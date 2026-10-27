from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Workline Profile & Role'


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'profile__role')

    def get_role(self, instance):
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else '-'
    get_role.short_description = 'Role'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
