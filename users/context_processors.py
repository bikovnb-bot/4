from .models import UserRole

def user_role(request):
    """Добавляет роль пользователя и флаги в контекст шаблона"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            role = request.user.profile.role
            is_super = request.user.is_superuser
            
            # Новые флаги (можно использовать в шаблонах)
            is_admin_flag = is_super or role == UserRole.ADMIN
            is_contract_specialist = is_super or role == UserRole.CONTRACT_SPECIALIST
            is_engineer = is_super or role == UserRole.ENGINEER
            is_dispatcher = is_super or role == UserRole.DISPATCHER
            is_worker = is_super or role == UserRole.WORKER
            
            # Старые флаги (для обратной совместимости шаблонов)
            is_manager = is_super or role == UserRole.CONTRACT_SPECIALIST
            is_viewer = is_super or role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER, UserRole.DISPATCHER]
            is_contractor = is_super or role == UserRole.WORKER
            
            return {
                'user_role': role,
                'is_admin': is_admin_flag,
                'is_manager': is_manager,
                'is_viewer': is_viewer,
                'is_contractor': is_contractor,
                # Новые для удобства
                'is_contract_specialist': is_contract_specialist,
                'is_engineer': is_engineer,
                'is_dispatcher': is_dispatcher,
                'is_worker': is_worker,
            }
        else:
            # Если профиля нет, создаём с ролью WORKER (по умолчанию)
            from .models import Profile
            Profile.objects.create(user=request.user, role=UserRole.WORKER)
            return {
                'user_role': UserRole.WORKER,
                'is_admin': False,
                'is_manager': False,
                'is_viewer': True,
                'is_contractor': True,
                'is_contract_specialist': False,
                'is_engineer': False,
                'is_dispatcher': False,
                'is_worker': True,
            }
    return {
        'user_role': None,
        'is_admin': False,
        'is_manager': False,
        'is_viewer': False,
        'is_contractor': False,
        'is_contract_specialist': False,
        'is_engineer': False,
        'is_dispatcher': False,
        'is_worker': False,
    }

def user_permissions(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return {
            'user_permissions': request.user.profile.get_all_permissions(),
        }
    return {'user_permissions': set()}