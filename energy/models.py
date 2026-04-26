from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class ResourceType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Тип ресурса")
    unit = models.CharField(max_length=10, verbose_name="Единица измерения")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип ресурса"
        verbose_name_plural = "Типы ресурсов"


class TariffComponent(models.Model):
    resource_type = models.ForeignKey(ResourceType, on_delete=models.CASCADE, verbose_name="Тип ресурса")
    name = models.CharField(max_length=50, verbose_name="Название компонента")
    unit = models.CharField(max_length=10, blank=True, verbose_name="Единица (оставьте пустой, чтобы брать из ресурса)")
    is_multi_tariff_zone = models.BooleanField(default=False, verbose_name="Является зоной дня/ночи?")
    valid_from = models.DateField(verbose_name="Действует с")
    valid_to = models.DateField(null=True, blank=True, verbose_name="Действует по")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу")

    def __str__(self):
        unit_display = self.unit or self.resource_type.unit
        return f"{self.resource_type.name} – {self.name}: {self.price} руб/{unit_display}"

    class Meta:
        ordering = ['resource_type', 'name', '-valid_from']
        unique_together = ['resource_type', 'name', 'valid_from']
        verbose_name = "Компонент тарифа"
        verbose_name_plural = "Компоненты тарифов"


class Meter(models.Model):
    serial_number = models.CharField(max_length=50, unique=True, verbose_name="Серийный номер / Название счётчика")
    resource_type = models.ForeignKey(ResourceType, on_delete=models.CASCADE, verbose_name="Тип ресурса")
    location = models.CharField(max_length=200, blank=True, verbose_name="Местоположение")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    transformation_ratio = models.DecimalField(
        max_digits=10, decimal_places=3, default=1.0,
        verbose_name="Коэффициент трансформации",
        help_text="Для электроэнергии (трансформаторы). Для воды и тепла оставьте 1."
    )
    is_multi_tariff = models.BooleanField(
        default=False,
        verbose_name="Многотарифный счётчик",
        help_text="Отметьте, если счётчик поддерживает разные тарифы по зонам (день/ночь/пик)"
    )
    initial_value = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name="Начальное показание",
        help_text="Для однотарифных счётчиков. Будет вычтено из первого показания."
    )

    def __str__(self):
        return self.serial_number

    def recalc_consumption(self):
        """Пересчитывает потребление для всех показаний счётчика в хронологическом порядке."""
        if hasattr(self, '_recalc_running') and self._recalc_running:
            return
        self._recalc_running = True
        try:
            readings = self.reading_set.order_by('date')
            if not readings:
                return

            if self.is_multi_tariff:
                from .models import TariffComponent, InitialZoneReading
                components = TariffComponent.objects.filter(resource_type=self.resource_type, is_multi_tariff_zone=True)
                for comp in components:
                    prev_value = None
                    for reading in readings:
                        try:
                            zr = ZoneReading.objects.get(reading=reading, tariff_component=comp)
                        except ZoneReading.DoesNotExist:
                            continue
                        if prev_value is not None:
                            raw = zr.value - prev_value
                        else:
                            initial = InitialZoneReading.objects.filter(meter=self, tariff_component=comp).first()
                            raw = zr.value - (initial.value if initial else 0)
                        new_consumption = raw * self.transformation_ratio
                        if zr.consumption != new_consumption:
                            zr.consumption = new_consumption
                            zr._skip_recalc = True
                            zr.save(update_fields=['consumption'])
                            del zr._skip_recalc
                        prev_value = zr.value
            else:
                prev_reading = None
                for reading in readings:
                    if reading.value is None:
                        continue
                    if prev_reading is not None:
                        raw = reading.value - prev_reading.value
                    else:
                        raw = reading.value - self.initial_value
                    new_consumption = raw * self.transformation_ratio
                    if reading.consumption != new_consumption:
                        reading.consumption = new_consumption
                        reading._skip_recalc = True
                        reading.save(update_fields=['consumption'])
                        del reading._skip_recalc
                    prev_reading = reading
        finally:
            del self._recalc_running

    class Meta:
        verbose_name = "Счётчик"
        verbose_name_plural = "Счётчики"


class InitialZoneReading(models.Model):
    meter = models.OneToOneField(Meter, on_delete=models.CASCADE, related_name='initial_zone_readings')
    tariff_component = models.ForeignKey(TariffComponent, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name="Начальное показание")

    class Meta:
        unique_together = ['meter', 'tariff_component']
        verbose_name = "Начальное показание по зоне"
        verbose_name_plural = "Начальные показания по зонам"

    def __str__(self):
        return f"{self.meter.serial_number} – {self.tariff_component.name}: {self.value}"


class Reading(models.Model):
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, verbose_name="Счётчик")
    date = models.DateField(verbose_name="Дата показания")
    value = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Показание (суммарное)")
    consumption = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Потребление")

    def total_consumption(self):
        if self.meter.is_multi_tariff:
            return sum(z.consumption or 0 for z in self.zone_readings.all())
        return self.consumption or 0

    def __str__(self):
        return f"{self.meter.serial_number} – {self.date}"

    class Meta:
        ordering = ['-date']
        unique_together = ['meter', 'date']
        verbose_name = "Показание"
        verbose_name_plural = "Показания"


class ZoneReading(models.Model):
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='zone_readings')
    tariff_component = models.ForeignKey(TariffComponent, on_delete=models.CASCADE, limit_choices_to={'is_multi_tariff_zone': True})
    value = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Показание по зоне")
    consumption = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Потребление по зоне")

    def save(self, *args, **kwargs):
        if not self.pk:
            prev = ZoneReading.objects.filter(
                reading__meter=self.reading.meter,
                tariff_component=self.tariff_component,
                reading__date__lt=self.reading.date
            ).order_by('-reading__date').first()
            if prev:
                raw = self.value - prev.value
            else:
                try:
                    initial = InitialZoneReading.objects.get(
                        meter=self.reading.meter,
                        tariff_component=self.tariff_component
                    )
                    raw = self.value - initial.value
                except InitialZoneReading.DoesNotExist:
                    raw = self.value
            self.consumption = raw * self.reading.meter.transformation_ratio
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reading.meter.serial_number} – {self.reading.date} – {self.tariff_component.name}: {self.value}"


class MeterDocument(models.Model):
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='documents', verbose_name="Счётчик")
    file = models.FileField(upload_to='meter_documents/%Y/%m/%d/', verbose_name="Файл")
    description = models.CharField(max_length=200, blank=True, verbose_name="Описание")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"{self.meter.serial_number} – {self.file.name}"

    def get_file_name(self):
        return self.file.name.split('/')[-1]

    class Meta:
        verbose_name = "Документ счётчика"
        verbose_name_plural = "Документы счётчиков"


class UserLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Создание'),
        ('EDIT', 'Редактирование'),
        ('DELETE', 'Удаление'),
        ('VIEW', 'Просмотр'),
        ('IMPORT', 'Импорт'),
        ('EXPORT', 'Экспорт'),
        ('LOGIN', 'Вход'),
        ('LOGOUT', 'Выход'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Действие")
    model_name = models.CharField(max_length=100, verbose_name="Модель", blank=True)
    object_id = models.CharField(max_length=50, verbose_name="ID объекта", blank=True)
    details = models.TextField(blank=True, verbose_name="Детали")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")

    class Meta:
        verbose_name = "Лог пользователя"
        verbose_name_plural = "Логи пользователей"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.timestamp}"
    
    # ------------------------------------------------------------
# Архивные модели
# ------------------------------------------------------------
class ArchivedReading(models.Model):
    meter = models.ForeignKey('Meter', on_delete=models.SET_NULL, null=True, verbose_name="Счётчик")
    date = models.DateField(verbose_name="Дата показания")
    value = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Показание (суммарное)")
    consumption = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Потребление")
    archived_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата архивации")

    class Meta:
        ordering = ['-date']
        verbose_name = "Архивное показание"
        verbose_name_plural = "Архивные показания"

    def __str__(self):
        if self.meter:
            return f"{self.meter.serial_number} – {self.date} (архив)"
        return f"Удалённый счётчик – {self.date} (архив)"


class ArchivedZoneReading(models.Model):
    archived_reading = models.ForeignKey(ArchivedReading, on_delete=models.CASCADE, related_name='zone_readings')
    tariff_component = models.ForeignKey('TariffComponent', on_delete=models.SET_NULL, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Показание по зоне")
    consumption = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="Потребление по зоне")

    def __str__(self):
        from .models import Meter  # локальный импорт для избежания циклической ссылки
        meter_info = self.archived_reading.meter.serial_number if self.archived_reading.meter else "?"
        return f"{meter_info} – {self.archived_reading.date} – {self.tariff_component.name} (архив)"