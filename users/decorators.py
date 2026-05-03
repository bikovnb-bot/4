# users/decorators.py

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from .models import UserRole

def is_admin(user):
    """Проверяет, является ли пользователь администратором"""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role == UserRole.ADMIN

def is_manager(user):
    """Проверяет, является ли пользователь менеджером или администратором"""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role in [UserRole.ADMIN, UserRole.MANAGER]

def is_viewer(user):
    """Проверяет, имеет ли пользователь право на просмотр"""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    # Разрешаем просмотр всем, включая CONTRACTOR (исполнитель)
    return user.profile.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER, UserRole.CONTRACTOR]

def is_contractor(user):
    """Проверяет, является ли пользователь исполнителем (подрядчиком)"""
    if not user.is_authenticated:
        return False
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role == UserRole.CONTRACTOR

def admin_required(view_func):
    """Декоратор: доступ только для администраторов"""
    @user_passes_test(is_admin, login_url='/accounts/login/')
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def manager_required(view_func):
    """Декоратор: доступ для менеджеров и администраторов"""
    @user_passes_test(is_manager, login_url='/accounts/login/')
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def viewer_required(view_func):
    """Декоратор: доступ для всех авторизованных пользователей (включая CONTRACTOR)"""
    @user_passes_test(is_viewer, login_url='/accounts/login/')
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def contractor_required(view_func):
    """Декоратор: доступ только для исполнителей (подрядчиков)"""
    @user_passes_test(is_contractor, login_url='/accounts/login/')
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper