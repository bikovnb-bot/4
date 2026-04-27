from users.decorators import is_viewer, is_manager, is_admin

def can_view_all_requests(user):
    return is_viewer(user)  # все авторизованные пользователи могут видеть (с фильтрами)

def can_edit_any_request(user):
    return is_manager(user)

def can_delete_request(user):
    return is_admin(user)

def can_assign_request(user):
    return is_manager(user) or is_admin(user)

def is_assignee_or_creator(user, request_obj):
    return request_obj.assigned_to == user or request_obj.created_by == user