# users/context_processors.py

from .utils import is_manager

def user_permissions(request):
    """
    Добавляет в контекст шаблонов информацию о правах пользователя.
    """
    if request.user.is_authenticated:
        return {
            'is_manager': is_manager(request.user),
            'is_viewer': is_manager(request.user) or request.user.groups.filter(name='Наблюдатели договоров').exists(),
        }
    return {
        'is_manager': False,
        'is_viewer': False,
    }