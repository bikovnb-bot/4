from django import forms
from django.contrib.auth.models import User
from .models import Meter, Reading, ZoneReading, TariffComponent, ResourceType, MeterDocument
from datetime import date
from .utils import can_assign_owner

# ------------------------------------------------------------
# Форма для добавления/редактирования счётчика
# ------------------------------------------------------------
class MeterForm(forms.ModelForm):
    class Meta:
        model = Meter
        fields = [
            'serial_number', 'resource_type', 'is_multi_tariff',
            'location', 'transformation_ratio', 'initial_value'
        ]
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'is_multi_tariff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'transformation_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'initial_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
        }
        labels = {
            'serial_number': 'Серийный номер / Название счётчика',
            'resource_type': 'Тип ресурса',
            'is_multi_tariff': 'Многотарифный',
            'location': 'Местоположение',
            'transformation_ratio': 'Коэффициент трансформации',
            'initial_value': 'Начальное показание',
        }
        help_texts = {
            'transformation_ratio': 'Для воды и тепла оставьте 1. Для электроэнергии укажите коэффициент (например, 20).',
            'initial_value': 'Начальное показание счётчика. Для многотарифных – начальные зоны задаются в админке.',
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['resource_type'].queryset = ResourceType.objects.all()
        # Поле user удалено из модели, поэтому не добавляем его в форму
        # if can_assign_owner(user):
        #     self.fields['user'] = forms.ModelChoiceField(queryset=User.objects.all(), label="Владелец", required=False)
        #     if self.instance and self.instance.pk:
        #         self.fields['user'].initial = self.instance.user

    def save(self, commit=True):
        meter = super().save(commit=False)
        # Поле user отсутствует, не пытаемся его присвоить
        if commit:
            meter.save()
        return meter


# ------------------------------------------------------------
# Форма для добавления показаний
# ------------------------------------------------------------
class ReadingForm(forms.Form):
    meter = forms.ModelChoiceField(queryset=Meter.objects.none(), label="Счётчик")
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Дата")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        from .utils import can_view_all_meters
        if can_view_all_meters(user):
            self.fields['meter'].queryset = Meter.objects.filter(is_active=True)
        else:
            self.fields['meter'].queryset = Meter.objects.filter(is_active=True)  # у нас нет user в Meter

        meter_id = self.data.get('meter') or self.initial.get('meter')
        date_str = self.data.get('date') or self.initial.get('date')

        if meter_id:
            try:
                meter = Meter.objects.get(pk=int(meter_id))
                if meter.is_multi_tariff:
                    if date_str:
                        target_date = date_str
                    else:
                        target_date = date.today().isoformat()
                    components = TariffComponent.objects.filter(
                        resource_type=meter.resource_type,
                        is_multi_tariff_zone=True,
                        valid_from__lte=target_date
                    ).exclude(valid_to__lt=target_date)
                    for comp in components:
                        field_name = f'zone_{comp.id}'
                        self.fields[field_name] = forms.DecimalField(
                            label=f"{comp.name} ({comp.unit or meter.resource_type.unit})",
                            max_digits=12, decimal_places=3,
                            widget=forms.NumberInput(attrs={'step': '0.001'})
                        )
                else:
                    self.fields['value'] = forms.DecimalField(
                        label=f"Показание ({meter.resource_type.unit})",
                        max_digits=12, decimal_places=3,
                        widget=forms.NumberInput(attrs={'step': '0.001'})
                    )
            except Meter.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        meter = cleaned_data.get('meter')
        date_val = cleaned_data.get('date')
        if not meter or not date_val:
            return cleaned_data

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=date_val
            ).exclude(valid_to__lt=date_val)
            for comp in components:
                field_name = f'zone_{comp.id}'
                val = cleaned_data.get(field_name)
                if val is None:
                    self.add_error(field_name, "Обязательное поле")
                    continue
                prev = ZoneReading.objects.filter(
                    reading__meter=meter,
                    tariff_component=comp,
                    reading__date__lt=date_val
                ).order_by('-reading__date').first()
                if prev and val <= prev.value:
                    self.add_error(field_name, f"Должно быть больше предыдущего ({prev.value})")
        else:
            value = cleaned_data.get('value')
            if value is None:
                self.add_error('value', "Обязательное поле")
            else:
                prev = Reading.objects.filter(meter=meter, date__lt=date_val).order_by('-date').first()
                if prev and prev.value is not None and value <= prev.value:
                    self.add_error('value', f"Должно быть больше предыдущего ({prev.value})")
        return cleaned_data

    def save(self):
        meter = self.cleaned_data['meter']
        date_val = self.cleaned_data['date']
        reading = Reading(meter=meter, date=date_val)

        if meter.is_multi_tariff:
            reading.save()
            for key, val in self.cleaned_data.items():
                if key.startswith('zone_'):
                    comp_id = int(key.split('_')[1])
                    comp = TariffComponent.objects.get(pk=comp_id)
                    ZoneReading.objects.create(reading=reading, tariff_component=comp, value=val)
            meter.recalc_consumption()
        else:
            reading.value = self.cleaned_data['value']
            reading.save()
        return reading


# ------------------------------------------------------------
# Форма для редактирования показаний
# ------------------------------------------------------------
class ReadingEditForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Дата")

    def __init__(self, user, reading, *args, **kwargs):
        self.user = user
        self.reading = reading
        meter = reading.meter
        super().__init__(*args, **kwargs)
        self.initial['date'] = reading.date

        # На основе существующего чтения определяем тип счётчика и добавляем поля зон или value
        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=reading.date
            ).exclude(valid_to__lt=reading.date)
            for comp in components:
                field_name = f'zone_{comp.id}'
                self.fields[field_name] = forms.DecimalField(
                    label=f"{comp.name} ({comp.unit or meter.resource_type.unit})",
                    max_digits=12, decimal_places=3,
                    widget=forms.NumberInput(attrs={'step': '0.001'})
                )
                zr = reading.zone_readings.filter(tariff_component=comp).first()
                if zr:
                    self.initial[field_name] = zr.value
        else:
            self.fields['value'] = forms.DecimalField(
                label=f"Показание ({meter.resource_type.unit})",
                max_digits=12, decimal_places=3,
                widget=forms.NumberInput(attrs={'step': '0.001'})
            )
            self.initial['value'] = reading.value

    def clean(self):
        cleaned_data = super().clean()
        reading = self.reading
        meter = reading.meter
        date_val = cleaned_data.get('date')
        if not date_val:
            return cleaned_data

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=date_val
            ).exclude(valid_to__lt=date_val)
            for comp in components:
                field_name = f'zone_{comp.id}'
                if field_name not in self.fields:
                    continue
                val = cleaned_data.get(field_name)
                if val is None:
                    self.add_error(field_name, "Обязательное поле")
                    continue
                prev = ZoneReading.objects.filter(
                    reading__meter=meter,
                    tariff_component=comp,
                    reading__date__lt=date_val
                ).exclude(reading__pk=reading.pk).order_by('-reading__date').first()
                if prev and val <= prev.value:
                    self.add_error(field_name, f"Должно быть больше предыдущего ({prev.value})")
        else:
            value = cleaned_data.get('value')
            if value is None:
                self.add_error('value', "Обязательное поле")
            else:
                prev = Reading.objects.filter(meter=meter, date__lt=date_val).exclude(pk=reading.pk).order_by('-date').first()
                if prev and prev.value is not None and value <= prev.value:
                    self.add_error('value', f"Должно быть больше предыдущего ({prev.value})")
        return cleaned_data

    def save(self):
        reading = self.reading
        reading.date = self.cleaned_data['date']
        meter = reading.meter

        if meter.is_multi_tariff:
            for key, val in self.cleaned_data.items():
                if key.startswith('zone_'):
                    comp_id = int(key.split('_')[1])
                    comp = TariffComponent.objects.get(pk=comp_id)
                    zr, created = ZoneReading.objects.update_or_create(
                        reading=reading,
                        tariff_component=comp,
                        defaults={'value': val}
                    )
                    zr.save()
            meter.recalc_consumption()
        else:
            reading.value = self.cleaned_data['value']
            previous = Reading.objects.filter(meter=meter, date__lt=reading.date).exclude(pk=reading.pk).order_by('-date').first()
            if previous:
                raw = reading.value - previous.value
                reading.consumption = raw * meter.transformation_ratio
            else:
                raw = reading.value - meter.initial_value
                reading.consumption = raw * meter.transformation_ratio
            reading.save(update_fields=['date', 'value', 'consumption'])
        reading.save(update_fields=['date'])
        return reading


# ------------------------------------------------------------
# Форма для загрузки документов счётчика
# ------------------------------------------------------------
class MeterDocumentForm(forms.ModelForm):
    class Meta:
        model = MeterDocument
        fields = ['file', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'file': 'Файл',
            'description': 'Описание (необязательно)',
        }


# ------------------------------------------------------------
# Форма для импорта показаний из Excel
# ------------------------------------------------------------
class ImportReadingsForm(forms.Form):
    excel_file = forms.FileField(label="Excel файл", help_text="Файл в формате .xlsx")
    dry_run = forms.BooleanField(label="Проверка без сохранения", required=False, initial=False)