from django.contrib import admin
from .models import ServiceRequest, RequestFile, RequestType, Material, UsedMaterial


class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 1
    fields = ('file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class UsedMaterialInline(admin.TabularInline):
    model = UsedMaterial
    extra = 0
    fields = ('name', 'quantity', 'unit', 'price_per_unit', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'default_price', 'quantity_in_stock')
    list_editable = ('quantity_in_stock',)
    search_fields = ('name',)
    list_filter = ('unit',)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'request_number', 'building', 'room_number', 'request_type',
        'priority', 'status', 'created_by', 'assigned_to', 'created_at'
    )
    list_filter = ('status', 'priority', 'request_type', 'building', 'created_at')
    search_fields = ('request_number', 'description', 'comment', 'building__name', 'room_number')
    autocomplete_fields = ('building', 'created_by', 'assigned_to')
    readonly_fields = ('request_number', 'created_at', 'updated_at', 'total_materials_cost')
    fieldsets = (
        (None, {
            'fields': ('request_number', 'building', 'room_number', 'request_type', 'description')
        }),
        ('Управление', {
            'fields': ('priority', 'status', 'assigned_to', 'planned_date', 'completed_date')
        }),
        ('Дополнительно', {
            'fields': ('comment', 'created_by', 'created_at', 'updated_at', 'total_materials_cost'),
            'classes': ('collapse',)
        }),
    )
    inlines = [RequestFileInline, UsedMaterialInline]

    def total_materials_cost(self, obj):
        total = sum(m.total_price for m in obj.used_materials.all())
        return f"{total} ₽" if total else "—"
    total_materials_cost.short_description = "Общая стоимость материалов"


@admin.register(UsedMaterial)
class UsedMaterialAdmin(admin.ModelAdmin):
    list_display = ('request', 'name', 'quantity', 'unit', 'price_per_unit', 'total_price')
    list_filter = ('request__status',)
    search_fields = ('name', 'request__request_number')
    readonly_fields = ('total_price',)


@admin.register(RequestFile)
class RequestFileAdmin(admin.ModelAdmin):
    list_display = ('request', 'get_file_name', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('request__request_number',)

    def get_file_name(self, obj):
        return obj.get_file_name()
    get_file_name.short_description = "Имя файла"