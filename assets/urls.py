# assets/urls.py
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Основные CRUD для имущества
    path('', views.AssetListView.as_view(), name='asset_list'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='asset_detail'),
    path('create/', views.AssetCreateView.as_view(), name='asset_create'),
    path('<int:pk>/edit/', views.AssetUpdateView.as_view(), name='asset_edit'),
    path('<int:pk>/delete/', views.AssetDeleteView.as_view(), name='asset_delete'),

    # Закрепление и возврат
    path('<int:pk>/assign/', views.assign_asset, name='assign_asset'),
    path('<int:pk>/return/', views.return_asset, name='return_asset'),

    # Проверки и QR-коды
    path('<int:pk>/check/', views.add_asset_check, name='add_check'),
    path('<int:pk>/qr/', views.generate_asset_qr, name='generate_qr'),
    path('<int:pk>/qr/download/', views.download_asset_qr, name='download_qr'),

    # Инвентаризация (отметка конкретного объекта)
    path('<int:pk>/inventory/', views.inventory_asset, name='inventory_asset'),  # <-- ДОБАВЛЕНО

    # Инвентаризация (общие страницы)
    path('inventory/', views.inventory_scan, name='inventory_scan'),
    path('inventory/scan-ajax/', views.inventory_scan_ajax, name='inventory_scan_ajax'),
    path('inventory/history/', views.inventory_history, name='inventory_history'),

    # Отчёты
    path('report/', views.asset_report, name='asset_report'),
]