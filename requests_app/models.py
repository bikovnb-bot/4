from django.db import models
from django.contrib.auth.models import User
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

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
        """Возвращает на склад все материалы, использованные в заявке, и удаляет записи UsedMaterial."""
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
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def get_file_name(self):
        return self.file.name.split('/')[-1]


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
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='used_materials', verbose_name="Заявка")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Количество")
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} – {self.quantity} {self.unit}"