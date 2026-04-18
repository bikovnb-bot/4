from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, UserRole

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    # Не создаём профиль через inlines, так как он создаётся сигналом

class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '—'
    get_role.short_description = 'Роль'
    
    def save_model(self, request, obj, form, change):
        """Сохраняем пользователя, профиль создаётся сигналом"""
        super().save_model(request, obj, form, change)
        # Если профиль не создался сигналом (например, при ошибке), создаём вручную
        if not hasattr(obj, 'profile'):
            Profile.objects.create(user=obj, role=UserRole.VIEWER)
            print(f"Профиль создан в админке для {obj.username}")

# Регистрируем кастомного админа
admin.site.unregister(User)
admin.site.register(User, UserAdmin)