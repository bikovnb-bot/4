from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # пользователи
    path('', views.user_list, name='user_list'),
    path('create/', views.user_create, name='user_create'),
    path('edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('toggle-active/<int:user_id>/', views.user_toggle_active, name='user_toggle_active'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('change-password/<int:user_id>/', views.user_change_password, name='user_change_password'),
    path('profile/', views.profile, name='profile'),
    # группы
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/edit/<int:group_id>/', views.group_edit, name='group_edit'),
    path('groups/delete/<int:group_id>/', views.group_delete, name='group_delete'),
    path('role-help/', views.role_help, name='role_help'),
]