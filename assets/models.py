# assets/models.py
import re
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.files import File
from django.urls import reverse
from django.conf import settings
from simple_history.models import HistoricalRecords
from io import BytesIO
import qrcode


class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка (CSS класс)")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категория имущества"
        verbose_name_plural = "Категории имущества"
        ordering = ['name']

    def __str__(self):
        return self.name


class Asset(models.Model):
    STATUS_CHOICES = [
        ('in_use', 'В эксплуатации'),
        ('in_stock', 'На складе'),
        ('under_repair', 'В ремонте'),
        ('written_off', 'Списано'),
        ('lost', 'Утеряно'),
    ]

    inventory_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Инвентарный номер",
        help_text="Оставьте пустым для автоматической генерации"
    )
    name = models.CharField(max_length=255, verbose_name="Наименование")
    category = models.ForeignKey(
        AssetCategory, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Балансовый счет", related_name='assets'
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    serial_number = models.CharField(max_length=100, blank=True, verbose_name="Серийный номер")
    manufacturer = models.CharField(max_length=100, blank=True, verbose_name="Производитель")
    model = models.CharField(max_length=100, blank=True, verbose_name="Модель")
    purchase_date = models.DateField(null=True, blank=True, verbose_name="Дата ввода в эксплуатацию")
    cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Балансовая стоимость (руб.)"
    )
    useful_life_months = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Срок полезного использования, мес.",
        help_text="Укажите срок полезного использования в месяцах"
    )
    location = models.CharField(max_length=255, blank=True, verbose_name="Местонахождение")
    responsible_person = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_assets', verbose_name="Ответственное лицо"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='in_stock',
        verbose_name="Статус"
    )
    qr_code = models.ImageField(
        upload_to='asset_qr/', blank=True, null=True,
        verbose_name="QR-код"
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    imported_from_excel = models.BooleanField(
        default=False,
        verbose_name="Импортировано из Excel",
        help_text="Отметка, что запись была создана при импорте из Excel"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Имущество"
        verbose_name_plural = "Имущество"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory_number']),
            models.Index(fields=['status']),
            models.Index(fields=['responsible_person']),
        ]

    def __str__(self):
        return f"{self.inventory_number} – {self.name}"

    def save(self, *args, **kwargs):
        if not self.inventory_number or not self.inventory_number.strip():
            self.inventory_number = self._generate_auto_inventory_number()
        super().save(*args, **kwargs)

    def _generate_auto_inventory_number(self):
        prefix = "Без номера"
        existing = Asset.objects.filter(
            inventory_number__startswith=prefix
        ).values_list('inventory_number', flat=True)

        max_num = 0
        pattern = re.compile(rf'^{re.escape(prefix)}\s+(\d+)$')
        for inv in existing:
            match = pattern.match(inv)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        return f"{prefix} {next_num:02d}"

    def generate_qr_code(self):
        """
        Генерирует QR-код, содержащий инвентарный номер объекта.
        При сканировании на странице инвентаризации этот номер используется
        для поиска имущества и отметки его в проверке.
        """
        if not self.pk or not self.inventory_number:
            return
        # Кодируем только инвентарный номер (без URL)
        data = self.inventory_number
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            self.qr_code.save(f"{self.inventory_number}.png", File(buffer), save=False)
        except ImportError:
            pass


class AssetAssignment(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='asset_assignments', verbose_name="Кому закреплено"
    )
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name="Дата закрепления")
    returned_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата возврата")
    notes = models.TextField(blank=True, verbose_name="Примечания")

    class Meta:
        verbose_name = "Закрепление имущества"
        verbose_name_plural = "Закрепления имущества"
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.asset} -> {self.assigned_to}"


class AssetCheck(models.Model):
    CONDITION_CHOICES = [
        ('good', 'Хорошее'),
        ('needs_repair', 'Требует ремонта'),
        ('damaged', 'Повреждено'),
        ('written_off', 'Списано'),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='checks')
    checked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='asset_checks', verbose_name="Проверил"
    )
    checked_at = models.DateTimeField(default=timezone.now, verbose_name="Дата проверки")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good', verbose_name="Состояние")
    notes = models.TextField(blank=True, verbose_name="Примечания")

    class Meta:
        verbose_name = "Проверка имущества"
        verbose_name_plural = "Проверки имущества"
        ordering = ['-checked_at']

    def __str__(self):
        return f"{self.asset} – {self.get_condition_display()}"


# ---------- СИГНАЛЫ ----------
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Asset)
def generate_asset_qr_on_save(sender, instance, created, **kwargs):
    """
    Генерирует QR-код после создания или если он отсутствует.
    """
    if created or not instance.qr_code:
        instance.generate_qr_code()
        if instance.qr_code:
            # Сохраняем только поле qr_code, чтобы избежать рекурсии
            instance.save(update_fields=['qr_code'])