from django.urls import path
from . import views

app_name = 'requests_app'

urlpatterns = [
    path('', views.request_list, name='request_list'),
    path('create/', views.request_create, name='request_create'),
    path('<int:pk>/', views.request_detail, name='request_detail'),
    path('<int:pk>/edit/', views.request_edit, name='request_edit'),
    path('<int:pk>/assign/', views.request_assign, name='request_assign'),
    # Заменяем execute на mark-completed, добавляем suspend и resume
    path('<int:pk>/mark-completed/', views.request_mark_completed, name='request_mark_completed'),
    path('<int:pk>/suspend/', views.request_suspend, name='request_suspend'),
    path('<int:pk>/resume/', views.request_resume, name='request_resume'),
    path('<int:pk>/close/', views.request_close, name='request_close'),
    path('dashboard/', views.request_dashboard, name='dashboard'),
    path('export-excel/', views.export_requests_excel, name='export_excel'),
    path('custom-report/', views.custom_report, name='custom_report'),
    path('materials/', views.material_stock, name='material_stock'),
    path('materials/export/', views.material_stock_export, name='material_stock_export'),
    path('import-materials/', views.import_materials, name='import_materials'),
    path('import-materials/template/', views.download_materials_template, name='download_materials_template'),
    path('<int:pk>/delete/', views.request_delete, name='request_delete'),
    path('materials/add/', views.material_add, name='material_add'),
    path('materials/<int:pk>/edit/', views.material_edit, name='material_edit'),
]