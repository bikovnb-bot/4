from django.urls import path
from . import views

app_name = 'requests_app'

urlpatterns = [
    path('', views.RequestListView.as_view(), name='request_list'),
    path('<int:pk>/', views.RequestDetailView.as_view(), name='request_detail'),
    path('create/', views.RequestCreateView.as_view(), name='request_create'),
    path('<int:pk>/edit/', views.RequestUpdateView.as_view(), name='request_edit'),
    path('<int:pk>/delete/', views.RequestDeleteView.as_view(), name='request_delete'),
    path('<int:pk>/close/', views.close_request, name='request_close'),  # добавить эту строку
    path('<int:pk>/delete-file/', views.delete_request_file, name='delete_request_file'),
    path('stock/', views.material_stock, name='material_stock'),
    path('stock/export/', views.material_stock_export, name='material_stock_export'),
    path('report/', views.custom_report, name='custom_report'),
    path('import-materials/', views.import_materials_from_excel, name='import_materials'),
    path('download-template/', views.download_materials_template, name='download_materials_template'),
]