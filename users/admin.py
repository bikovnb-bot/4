# users/admin.py

from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'position', 'department', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('position', 'department')