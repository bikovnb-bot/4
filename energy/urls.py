from django.urls import path
from . import views

app_name = 'energy'

urlpatterns = [
    # Приборы учёта (CRUD)
    path('meters/', views.MeterListView.as_view(), name='meter_list'),
    path('meters/add/', views.add_meter, name='add_meter'),
    path('meters/<int:pk>/', views.MeterDetailView.as_view(), name='meter_detail'),
    path('meters/<int:pk>/edit/', views.MeterUpdateView.as_view(), name='meter_edit'),
    path('meters/<int:pk>/delete/', views.MeterDeleteView.as_view(), name='meter_delete'),
    
    # Показания (добавление, редактирование, удаление)
    path('add-reading/', views.add_reading, name='add_reading'),
    path('add-reading-modal/', views.add_reading_modal, name='add_reading_modal'),
    path('reading/<int:pk>/edit/', views.edit_reading, name='reading_edit'),
    path('reading/<int:pk>/delete/', views.delete_reading, name='reading_delete'),
    
    # Документы
    path('meters/<int:meter_pk>/upload-doc/', views.upload_document, name='upload_document'),
    path('documents/<int:pk>/delete/', views.delete_document, name='delete_document'),
    
    # Отчёты
    path('report/consumption/', views.consumption_report, name='consumption_report'),
    path('report/export/', views.export_consumption_report, name='export_consumption_report'),
    path('report/anomaly/', views.anomaly_report, name='anomaly_report'),
    
    # Импорт/экспорт
    path('import/', views.import_readings, name='import_readings'),
    path('download-template/', views.download_import_template, name='download_import_template'),
    path('export-readings/', views.export_readings, name='export_readings'),
]