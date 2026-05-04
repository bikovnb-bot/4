from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from buildings.models import Building


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
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")
    track_time = models.BooleanField(default=False, verbose_name="Учитывать время выполнения")
    time_spent = models.PositiveIntegerField(null=True, blank=True, verbose_name="Затраченное время (минуты)")
    suspension_reason = models.TextField(blank=True, null=True, verbose_name="Причина приостановки")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def save(self, *args, **kwargs):
        if not self.request_number:
            last = ServiceRequest.objects.order_by('-id').first()
            new_id = (last.id + 1) if last else 1
            self.request_number = f"ЗЯ-{new_id:06d}"
        super().save(*args, **kwargs)

    def return_materials_to_stock(self):
        from .models import Material
        for used in self.used_materials.all():
            material = Material.objects.filter(name=used.name).first()
            if material:
                material.quantity_in_stock += used.quantity
                material.save()
        self.used_materials.all().delete()

    def __str__(self):
        return f"{self.request_number} - {self.building}"


class RequestFile(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='files', verbose_name="Заявка")
    file = models.FileField(upload_to='request_files/%Y/%m/%d/', verbose_name="Файл")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Кто загрузил")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def get_file_name(self):
        return self.file.name.split('/')[-1]

    def __str__(self):
        return self.get_file_name()


class Material(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Наименование")
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")
    default_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу")
    quantity_in_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name="Количество на складе")

    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"


class UsedMaterial(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='used_materials')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Материал")
    name = models.CharField(max_length=200, verbose_name="Наименование")  # историческая копия
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