# requests_app/models.py

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from buildings.models import Building, BuildingSection


class RequestNumberSequence(models.Model):
    """Счётчик для атомарной генерации номеров заявок."""
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Счётчик номеров заявок"
        verbose_name_plural = "Счётчики номеров заявок"


class RequestType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название типа")
    icon = models.CharField(max_length=20, blank=True, verbose_name="Иконка (emoji или класс)")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок сортировки")

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Тип заявки"
        verbose_name_plural = "Типы заявок"

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
    ]
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
        ('closed', 'Закрыта'),
        ('suspended', 'Приостановлена'),
    ]

    request_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Номер заявки")
    building = models.ForeignKey(Building, on_delete=models.CASCADE, verbose_name="Здание")
    section = models.ForeignKey(
        BuildingSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Часть здания"
    )
    room_number = models.CharField(max_length=20, verbose_name="Номер помещения")
    request_type = models.ForeignKey(RequestType, on_delete=models.PROTECT, verbose_name="Тип заявки")
    description = models.TextField(verbose_name="Описание")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Приоритет")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_requests', verbose_name="Создатель")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests', verbose_name="Ответственный")
    planned_date = models.DateField(null=True, blank=True, verbose_name="Плановая дата выполнения")
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(verbose_name="Создана", editable=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")
    track_time = models.BooleanField(default=False, verbose_name="Учитывать время выполнения")
    time_spent = models.PositiveIntegerField(null=True, blank=True, verbose_name="Затраченное время (минуты)")
    suspension_reason = models.TextField(blank=True, null=True, verbose_name="Причина приостановки")

    contact_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Контактное лицо")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP адрес")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['planned_date']),
        ]

    def clean(self):
        """Валидация на уровне модели (пользовательские проверки)."""
        # Плановая дата не может быть в прошлом только для новых заявок
        if not self.pk and self.planned_date and self.planned_date < timezone.now().date():
            raise ValidationError({'planned_date': 'Плановая дата для новой заявки не может быть в прошлом.'})
        if self.completed_date and self.created_at and self.completed_date < self.created_at:
            raise ValidationError({'completed_date': 'Дата выполнения не может быть раньше даты создания.'})
        if self.section and self.building and self.section.building != self.building:
            raise ValidationError({'section': 'Секция не принадлежит выбранному зданию.'})

    def save(self, *args, **kwargs):
        if not self.request_number:
            from django.db import transaction
            with transaction.atomic():
                seq = RequestNumberSequence.objects.select_for_update().first()
                if seq is None:
                    seq = RequestNumberSequence.objects.create(last_number=0)
                seq.last_number += 1
                seq.save()
                self.request_number = f"ЗЯ-{seq.last_number:06d}"
        if not self.created_at:
            self.created_at = timezone.now()
        # Вызываем только наши пользовательские проверки (не full_clean, чтобы не блокировать null-поля)
        self.clean()
        super().save(*args, **kwargs)

    def return_materials_to_stock(self):
        """Возвращает использованные материалы на склад (при откате из closed)."""
        from .models import Material, MaterialTransaction
        for used in self.used_materials.all():
            material = used.material
            # fallback на случай, если material = None (например, из бэкапа)
            if not material:
                material = Material.objects.filter(name=used.name).first()
            if material:
                material.quantity_in_stock += used.quantity
                material.save()
                MaterialTransaction.objects.create(
                    material=material,
                    request=self,
                    quantity=used.quantity,
                    transaction_type='return',
                    comment=f'Возврат при изменении статуса с closed на другой'
                )
        self.used_materials.all().delete()

    def get_creator_display(self):
        if self.created_by:
            return self.created_by.get_full_name() or self.created_by.username
        elif self.contact_name:
            return self.contact_name
        else:
            return "Публичная"

    def __str__(self):
        return f"{self.request_number} - {self.building}"


class RequestAssignee(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='assignees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_to_requests')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['request', 'user']
        verbose_name = 'Назначенный исполнитель'
        verbose_name_plural = 'Назначенные исполнители'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} -> {self.request.request_number}'


class RequestFile(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='files', verbose_name="Файлы")
    file = models.FileField(upload_to='request_files/%Y/%m/%d/', null=True, blank=True, verbose_name="Файл")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Кто загрузил")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")

    def get_file_name(self):
        return self.file.name.split('/')[-1] if self.file else ''

    def __str__(self):
        return self.get_file_name() or 'Файл без имени'


class Material(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Наименование")
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")
    default_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу")
    quantity_in_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name="Количество на складе")
    min_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name="Минимальный остаток")

    def __str__(self):
        return f"{self.name} ({self.unit})"

    def is_low_stock(self):
        """Проверяет, не ниже ли остаток минимального порога."""
        return self.quantity_in_stock <= self.min_stock

    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"


class UsedMaterial(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='used_materials')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Материал")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} – {self.quantity} {self.unit}"


class RequestHistory(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    action = models.CharField(max_length=255, verbose_name='Действие')
    old_value = models.TextField(blank=True, null=True, verbose_name='Старое значение')
    new_value = models.TextField(blank=True, null=True, verbose_name='Новое значение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'История заявки'
        verbose_name_plural = 'История заявок'

    def __str__(self):
        return f'{self.request.request_number} - {self.action} - {self.created_at}'


class RequestSettings(models.Model):
    default_building = models.ForeignKey(
        'buildings.Building',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Здание по умолчанию для новых заявок"
    )
    single_building = models.BooleanField(
        default=False,
        verbose_name="Единственное здание",
        help_text="Если включено, поле выбора здания скрывается, и все заявки создаются только для здания по умолчанию"
    )

    class Meta:
        verbose_name = "Настройки заявок"
        verbose_name_plural = "Настройки заявок"

    def save(self, *args, **kwargs):
        if not self.pk and RequestSettings.objects.exists():
            raise ValidationError("Может существовать только одна запись настроек.")
        super().save(*args, **kwargs)

    def __str__(self):
        return "Настройки заявок"


class MaterialTransaction(models.Model):
    """Аудит движения материалов."""
    TRANSACTION_TYPES = (
        ('in', 'Поступление'),
        ('out', 'Списание'),
        ('return', 'Возврат'),
    )
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='transactions')
    request = models.ForeignKey(ServiceRequest, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Транзакция материала'
        verbose_name_plural = 'Транзакции материалов'

    def __str__(self):
        return f'{self.material.name} {self.get_transaction_type_display()} {self.quantity}'