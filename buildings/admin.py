# buildings/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Building, BuildingDocument
from exploitation_app.models import OperationContract


class BuildingDocumentInline(admin.TabularInline):
    """Inline-форма для документов здания"""
    model = BuildingDocument
    extra = 1
    fields = ('file_link', 'title', 'file', 'uploaded_at')
    readonly_fields = ('file_link', 'uploaded_at')
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file.url)
        return "—"
    file_link.short_description = 'Файл'


class OperationContractInline(admin.TabularInline):
    """Inline-форма для договоров, связанных со зданием"""
    model = OperationContract
    fk_name = 'building'  # ← указываем поле ForeignKey
    extra = 0
    fields = ('contract_number', 'contract_type', 'contractor', 'status', 'start_date', 'end_date')
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    """Админка для управления зданиями"""
    inlines = [BuildingDocumentInline, OperationContractInline]
    list_display = ('name', 'address', 'cadastral_number', 'total_area', 'year_built', 'building_type')
    list_filter = ('building_type', 'wall_material', 'year_built')
    search_fields = ('name', 'address', 'cadastral_number')
    readonly_fields = ('total_area', 'created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'cadastral_number', 'address')
        }),
        ('Площади', {
            'fields': ('residential_area', 'non_residential_area', 'total_area'),
            'description': 'Общая площадь вычисляется автоматически как сумма жилой и нежилой.'
        }),
        ('Характеристики', {
            'fields': ('number_of_floors', 'year_built', 'wall_material', 
                       'foundation_type', 'number_of_rooms', 'building_type')
        }),
        ('Системные поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BuildingDocument)
class BuildingDocumentAdmin(admin.ModelAdmin):
    """Админка для управления документами зданий"""
    list_display = ('title', 'building', 'file_link', 'uploaded_at')
    list_filter = ('uploaded_at', 'building')
    search_fields = ('title', 'building__name', 'building__address')
    readonly_fields = ('uploaded_at', 'file_link')
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file.url)
        return "—"
    file_link.short_description = 'Файл'