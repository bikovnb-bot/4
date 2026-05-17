from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from .models import UserRole

# ---- Базовые проверки ролей ----
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == UserRole.ADMIN))

def is_contract_specialist(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == UserRole.CONTRACT_SPECIALIST

def is_engineer(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == UserRole.ENGINEER

def is_dispatcher(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == UserRole.DISPATCHER

def is_worker(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == UserRole.WORKER

# ---- Комбинированные проверки ----
def has_contract_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    role = user.profile.role
    return role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER]

def has_contract_edit_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    role = user.profile.role
    return role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER]

def has_ticket_full_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    role = user.profile.role
    return role in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]

def has_ticket_assigned_only(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    role = user.profile.role
    return role == UserRole.WORKER

# ---- Декораторы для конкретных ролей ----
def admin_required(view_func):
    @user_passes_test(is_admin, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def contract_specialist_required(view_func):
    @user_passes_test(is_contract_specialist, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def engineer_required(view_func):
    @user_passes_test(is_engineer, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def dispatcher_required(view_func):
    @user_passes_test(is_dispatcher, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def worker_required(view_func):
    @user_passes_test(is_worker, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

# ---- Декораторы для модулей ----
def contract_access_required(view_func):
    @user_passes_test(has_contract_access, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def contract_edit_required(view_func):
    @user_passes_test(has_contract_edit_access, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def ticket_full_access_required(view_func):
    @user_passes_test(has_ticket_full_access, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def ticket_assigned_only_required(view_func):
    @user_passes_test(has_ticket_assigned_only, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

# ---------- ОБРАТНАЯ СОВМЕСТИМОСТЬ ----------
def is_viewer(user):
    return user.is_authenticated

def is_manager(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role == UserRole.CONTRACT_SPECIALIST

def is_contractor(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role == UserRole.WORKER

def manager_required(view_func):
    @user_passes_test(is_manager, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def viewer_required(view_func):
    @user_passes_test(lambda u: u.is_authenticated, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def contractor_required(view_func):
    @user_passes_test(is_contractor, login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper

def has_perm(user, perm):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.has_perm(perm)
    return user.has_perm(perm)

def perm_required(perm):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_perm(request.user, perm):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator