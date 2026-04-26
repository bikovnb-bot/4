from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import ResourceType, TariffComponent, Meter, Reading, ZoneReading, InitialZoneReading, MeterDocument, UserLog

class InitialZoneReadingInline(admin.TabularInline):
    model = InitialZoneReading
    extra = 1
    fields = ('tariff_component', 'value')
    verbose_name = "Начальное показание по зоне"
    verbose_name_plural = "Начальные показания по зонам"

class ZoneReadingInline(admin.TabularInline):
    model = ZoneReading
    extra = 0
    fields = ('tariff_component', 'value', 'consumption')
    readonly_fields = ('consumption',)
    show_change_link = True
    can_delete = True

@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit')
    search_fields = ('name',)

@admin.register(TariffComponent)
class TariffComponentAdmin(admin.ModelAdmin):
    list_display = ('resource_type', 'name', 'price', 'valid_from', 'valid_to', 'is_multi_tariff_zone')
    list_filter = ('resource_type', 'is_multi_tariff_zone')
    search_fields = ('name',)

@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'resource_type', 'is_multi_tariff', 'transformation_ratio', 'initial_value', 'is_active')
    list_filter = ('resource_type', 'is_multi_tariff', 'is_active')
    search_fields = ('serial_number',)
    fields = ('serial_number', 'resource_type', 'is_multi_tariff', 'location', 'transformation_ratio', 'initial_value', 'is_active')
    inlines = [InitialZoneReadingInline]
    readonly_fields = ('meter_type_info',)

    def meter_type_info(self, obj):
        if obj.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=obj.resource_type,
                is_multi_tariff_zone=True
            )
            if components.exists():
                links = []
                for comp in components:
                    url = reverse('admin:energy_tariffcomponent_change', args=[comp.id])
                    links.append(format_html('<a href="{}">{}</a>', url, comp.name))
                return format_html("Зоны: {}", ", ".join(links))
            else:
                return "Нет зон (создайте компоненты тарифа с флагом 'зона')"
        return "Однотарифный"
    meter_type_info.short_description = "Тарифная информация"

@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('meter', 'date', 'total_consumption_display')
    list_filter = ('meter__resource_type', 'date')
    date_hierarchy = 'date'
    readonly_fields = ('total_consumption_display',)
    fields = ('meter', 'date', 'value')
    inlines = [ZoneReadingInline]

    def total_consumption_display(self, obj):
        return f"{obj.total_consumption()} {obj.meter.resource_type.unit}"
    total_consumption_display.short_description = "Потребление"

@admin.register(ZoneReading)
class ZoneReadingAdmin(admin.ModelAdmin):
    list_display = ('reading', 'tariff_component', 'value', 'consumption')
    list_filter = ('tariff_component',)
    readonly_fields = ('consumption',)

@admin.register(MeterDocument)
class MeterDocumentAdmin(admin.ModelAdmin):
    list_display = ('meter', 'get_file_name', 'uploaded_at')
    list_filter = ('meter',)
    search_fields = ('meter__serial_number',)
    readonly_fields = ('uploaded_at',)
    fields = ('meter', 'file', 'description', 'uploaded_at')

    def get_file_name(self, obj):
        return obj.get_file_name()
    get_file_name.short_description = "Файл"

@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('user__username', 'model_name', 'object_id', 'details')
    readonly_fields = ('timestamp',)
    fields = ('user', 'action', 'model_name', 'object_id', 'details', 'ip_address', 'timestamp')