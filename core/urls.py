# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.unified_dashboard, name='unified_dashboard'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('login/', views.CustomLoginView.as_view(), name='login'),  # <-- новый маршрут
]