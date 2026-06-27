from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import date
from simple_history.admin import SimpleHistoryAdmin
from .models import Asset, AssetCategory, AssetAssignment, AssetCheck, AssetPhoto


# ---------- ДЕЙСТВИЯ (ACTIONS) ----------
@admin.action(description='Сгенерировать QR-коды для выбранных объектов')
def generate_qr_codes(modeladmin, request, queryset):
    for asset in queryset:
        if not asset.qr_code:
            asset.generate_qr_code()
            asset.save(update_fields=['qr_code'])
    modeladmin.message_user(request, f'QR-коды сгенерированы для {queryset.count()} объектов.')

@admin.action(description='Изменить статус на "В эксплуатации"')
def set_status_in_use(modeladmin, request, queryset):
    queryset.update(status='in_use')

@admin.action(description='Изменить статус на "На складе"')
def set_status_in_stock(modeladmin, request, queryset):
    queryset.update(status='in_stock')

@admin.action(description='Изменить статус на "Списано"')
def set_status_written_off(modeladmin, request, queryset):
    queryset.update(status='written_off')

@admin.action(description='Изменить категорию на выбранную')
def change_category(modeladmin, request, queryset):
    # Можно добавить промежуточную страницу для выбора категории, но для простоты используем первую попавшуюся
    # Лучше реализовать через admin action с формой, но пока оставим как пример.
    # Для реального использования рекомендую создать промежуточную страницу.
    pass


# ---------- INLINE ДЛЯ ФОТОГРАФИЙ ----------
class AssetPhotoInline(admin.TabularInline):
    model = AssetPhoto
    extra = 0
    fields = ('image', 'caption', 'order')
    show_change_link = True
    can_delete = True


# ---------- РЕГИСТРАЦИЯ МОДЕЛЕЙ ----------
@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name',)
    list_editable = ('icon',)


@admin.register(Asset)
class AssetAdmin(SimpleHistoryAdmin):
    # Отображение в списке
    list_display = (
        'inventory_number', 'name', 'category', 'status', 'status_colored',
        'responsible_person', 'location', 'cost', 'age_display', 'has_qr'
    )
    list_filter = ('status', 'category', 'purchase_date', 'created_at', 'responsible_person')
    search_fields = ('inventory_number', 'name', 'serial_number', 'location', 'manufacturer', 'model')
    autocomplete_fields = ('category', 'responsible_person')  # удобный поиск
    readonly_fields = ('inventory_number', 'qr_code', 'created_at', 'updated_at')
    list_editable = ('status', 'responsible_person', 'category')  # можно менять прямо из списка
    list_select_related = ('category', 'responsible_person')
    list_per_page = 25
    save_on_top = True
    actions = [generate_qr_codes, set_status_in_use, set_status_in_stock, set_status_written_off]
    inlines = [AssetPhotoInline]   # добавлено!

    # Группировка полей в форме
    fieldsets = (
        (None, {
            'fields': ('inventory_number', 'name', 'category', 'description')
        }),
        ('Характеристики', {
            'fields': ('serial_number', 'manufacturer', 'model', 'purchase_date', 'cost', 'useful_life_months'),
            'classes': ('collapse',)  # свернуть по умолчанию
        }),
        ('Место и статус', {
            'fields': ('location', 'responsible_person', 'status')
        }),
        ('Дополнительно', {
            'fields': ('qr_code', 'notes', 'imported_from_excel'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ---------- КАСТОМНЫЕ МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ----------
    def status_colored(self, obj):
        colors = {
            'in_use': '#2e7d32',      # зелёный
            'in_stock': '#1565c0',    # синий
            'under_repair': '#e65100', # оранжевый
            'written_off': '#b71c1c', # красный
            'lost': '#757575',        # серый
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Статус'

    def has_qr(self, obj):
        return bool(obj.qr_code)
    has_qr.boolean = True
    has_qr.short_description = 'QR'

    def age_display(self, obj):
        """Возраст имущества (лет с момента покупки)"""
        if not obj.purchase_date:
            return '-'
        today = date.today()
        years = today.year - obj.purchase_date.year
        if today.month < obj.purchase_date.month or (today.month == obj.purchase_date.month and today.day < obj.purchase_date.day):
            years -= 1
        return f'{years} лет' if years else '< 1 года'
    age_display.short_description = 'Возраст'

    # Дополнительно: ссылка на просмотр QR-кода (если хотите)
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return '-'
    qr_preview.short_description = 'QR-код'


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'assigned_to', 'assigned_at', 'returned_at')
    list_filter = ('assigned_at', 'returned_at')
    autocomplete_fields = ('asset', 'assigned_to')
    search_fields = ('asset__inventory_number', 'asset__name', 'assigned_to__username')
    list_select_related = ('asset', 'assigned_to')


@admin.register(AssetCheck)
class AssetCheckAdmin(admin.ModelAdmin):
    list_display = ('asset', 'checked_by', 'checked_at', 'condition')
    list_filter = ('condition', 'checked_at')
    autocomplete_fields = ('asset', 'checked_by')
    search_fields = ('asset__inventory_number', 'asset__name')
    list_select_related = ('asset', 'checked_by')


@admin.register(AssetPhoto)
class AssetPhotoAdmin(admin.ModelAdmin):
    list_display = ('asset', 'image_preview', 'caption', 'order', 'uploaded_at')
    list_editable = ('order', 'caption')
    list_filter = ('uploaded_at',)
    search_fields = ('asset__inventory_number', 'asset__name', 'caption')
    autocomplete_fields = ('asset',)
    readonly_fields = ('uploaded_at',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Превью'