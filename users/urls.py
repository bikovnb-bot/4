from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('profile/', views.profile, name='profile'),
    path('toggle-active/<int:user_id>/', views.user_toggle_active, name='user_toggle_active'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('change-password/<int:user_id>/', views.user_change_password, name='user_change_password'),
    # Кастомные login/logout удалены — используем стандартные Django
]