# users/utils.py
from django.db.models import Q
from .models import UserRole

# Импорт модели OperationContract делаем внутри функций, чтобы избежать циклического импорта
# (т.к. exploitation_app может импортировать users.utils)

def can_edit_contract(user, contract):
    """Проверяет, может ли пользователь редактировать конкретный договор"""
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False

    if user.profile.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return True

    if user.profile.role == UserRole.CONTRACTOR:
        return (contract.contractor == user.username or
                contract.contractor_contact == user.get_full_name())

    return False


def can_view_contract(user, contract):
    """Проверяет, может ли пользователь просматривать договор"""
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False

    if user.profile.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER]:
        return True

    if user.profile.role == UserRole.CONTRACTOR:
        return (contract.contractor == user.username or
                contract.contractor_contact == user.get_full_name())

    return False


def get_visible_contracts(user):
    """
    Возвращает QuerySet договоров, доступных пользователю.
    Используется во всех представлениях, где нужно отфильтровать список договоров.
    """
    # Локальный импорт для избежания циклической зависимости
    from exploitation_app.models import OperationContract

    if not user.is_authenticated:
        return OperationContract.objects.none()

    if user.is_superuser:
        return OperationContract.objects.all()

    if not hasattr(user, 'profile'):
        return OperationContract.objects.none()

    role = user.profile.role

    if role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER]:
        return OperationContract.objects.all()

    if role == UserRole.CONTRACTOR:
        return OperationContract.objects.filter(
            Q(contractor=user.username) |
            Q(contractor_contact=user.get_full_name())
        )

    # Если роль не определена или неизвестна
    return OperationContract.objects.none()