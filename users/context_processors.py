from .models import UserRole

def user_role(request):
    """Добавляет роль пользователя в контекст шаблона"""
    if request.user.is_authenticated:
        # Проверяем, есть ли профиль у пользователя
        if hasattr(request.user, 'profile'):
            return {
                'user_role': request.user.profile.role,
                'is_admin': request.user.profile.role == UserRole.ADMIN or request.user.is_superuser,
                'is_manager': request.user.profile.role in [UserRole.ADMIN, UserRole.MANAGER] or request.user.is_superuser,
                'is_viewer': request.user.profile.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER] or request.user.is_superuser,
                'is_contractor': request.user.profile.role == UserRole.CONTRACTOR,
            }
        else:
            # Если профиля нет, создаём его
            from .models import Profile
            Profile.objects.create(user=request.user, role=UserRole.VIEWER)
            return {
                'user_role': UserRole.VIEWER,
                'is_admin': False,
                'is_manager': False,
                'is_viewer': True,
                'is_contractor': False,
            }
    return {
        'user_role': None,
        'is_admin': False,
        'is_manager': False,
        'is_viewer': False,
        'is_contractor': False,
    }