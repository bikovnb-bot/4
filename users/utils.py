from .models import UserRole

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