# buildings/models.py

import os
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

def validate_pdf(value):
    """Валидатор: разрешены только файлы с расширением .pdf"""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError('Разрешены только PDF-файлы.')


class Building(models.Model):
    # Название здания
    name = models.CharField(
        max_length=200,
        verbose_name="Название здания",
        help_text="Например: 'Торговый центр Европа', 'Бизнес-центр Плаза'",
        blank=False,
        default=''
    )

    # Основные идентификационные данные
    cadastral_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Кадастровый номер"
    )
    address = models.CharField(
        max_length=255,
        verbose_name="Адрес здания"
    )

    # Жилая и нежилая площадь
    residential_area = models.FloatField(
        validators=[MinValueValidator(0.0)],
        default=0.0,
        verbose_name="Жилая площадь (м²)"
    )
    non_residential_area = models.FloatField(
        validators=[MinValueValidator(0.0)],
        default=0.0,
        verbose_name="Нежилая площадь (м²)"
    )

    # Общая площадь – автоматически вычисляется как сумма жилой и нежилой
    total_area = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name="Общая площадь (м²)",
        editable=False
    )

    # Физические характеристики
    number_of_floors = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество этажей"
    )
    year_built = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1800), MaxValueValidator(2026)],
        verbose_name="Год постройки"
    )

    # Материалы и конструкция
    class MaterialType(models.TextChoices):
        BRICK = 'BR', 'Кирпич'
        CONCRETE = 'CN', 'Железобетон'
        WOOD = 'WD', 'Дерево'
        METAL = 'MT', 'Металл'
        OTHER = 'OT', 'Другое'

    wall_material = models.CharField(
        max_length=2,
        choices=MaterialType.choices,
        default=MaterialType.BRICK,
        verbose_name="Материал стен"
    )

    foundation_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Тип фундамента"
    )

    # Количественные показатели
    number_of_rooms = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество помещений"
    )

    # Тип здания
    class BuildingType(models.TextChoices):
        RESIDENTIAL = 'RES', 'Жилое'
        ADMINISTRATIVE = 'ADM', 'Административное'
        PUBLIC = 'PUB', 'Общественное'
        INDUSTRIAL = 'IND', 'Производственное'

    building_type = models.CharField(
        max_length=3,
        choices=BuildingType.choices,
        default=BuildingType.RESIDENTIAL,
        verbose_name="Тип здания"
    )

    # Дополнительные атрибуты
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Здание"
        verbose_name_plural = "Здания"
        ordering = ['-year_built', 'address']

    def save(self, *args, **kwargs):
        # Автоматически вычисляем общую площадь перед сохранением
        self.total_area = self.residential_area + self.non_residential_area
        super().save(*args, **kwargs)

    def __str__(self):
        # Короткое представление: либо название, либо первые две части адреса
        if self.name:
            return self.name
        # Убираем кадастровый номер и лишнее из адреса
        address = self.address
        parts = address.split(',')
        if len(parts) >= 2:
            return ', '.join(parts[:2]).strip()
        return address.strip()


class BuildingDocument(models.Model):
    """Модель для хранения PDF-документов, связанных со зданием"""
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Здание"
    )
    file = models.FileField(
        upload_to='building_documents/%Y/%m/%d/',
        validators=[validate_pdf],
        verbose_name="Файл документа (PDF)"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Название документа",
        help_text="Необязательное название (например, 'Технический паспорт')"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата загрузки"
    )

    class Meta:
        verbose_name = "Документ здания"
        verbose_name_plural = "Документы зданий"
        ordering = ['-uploaded_at']

    def __str__(self):
        if self.title:
            return f"{self.title} ({self.building})"
        return f"Документ от {self.uploaded_at.date()} для {self.building}"