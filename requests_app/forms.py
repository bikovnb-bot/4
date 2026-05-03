from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import ServiceRequest, RequestFile, RequestType, UsedMaterial, Material
from buildings.models import Building


class ServiceRequestForm(forms.ModelForm):
    """Упрощённая форма создания/редактирования заявки (только основные поля)"""
    planned_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Плановая дата выполнения'
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'building',
            'room_number',
            'request_type',
            'description',
            'priority',
            'planned_date',
        ]
        widgets = {
            'building': forms.Select(attrs={'class': 'form-select'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 117'}),
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Опишите проблему...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'planned_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'building': 'Здание',
            'room_number': 'Номер помещения',
            'request_type': 'Тип заявки',
            'description': 'Описание',
            'priority': 'Приоритет',
            'planned_date': 'Плановая дата',
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_type'].queryset = RequestType.objects.filter(is_active=True)
        # Если в будущем у Building появится is_active, можно раскомментировать:
        # self.fields['building'].queryset = Building.objects.filter(is_active=True)


class RequestFileForm(forms.ModelForm):
    """Форма для загрузки файлов к заявке"""
    class Meta:
        model = RequestFile
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }


# Формсет для материалов (используется при закрытии заявки и в деталях)
class UsedMaterialForm(forms.ModelForm):
    class Meta:
        model = UsedMaterial
        fields = ['material', 'quantity', 'unit', 'price_per_unit']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.all()
        self.fields['material'].label_from_instance = lambda obj: f"{obj.name} ({obj.unit})"

UsedMaterialFormSet = inlineformset_factory(
    ServiceRequest,
    UsedMaterial,
    form=UsedMaterialForm,
    extra=3,
    can_delete=True,
)


# Форма для настраиваемого отчёта по заявкам
class ReportForm(forms.Form):
    columns = forms.MultipleChoiceField(
        choices=[
            ('request_number', '№ заявки'),
            ('building', 'Здание'),
            ('room_number', 'Помещение'),
            ('request_type', 'Тип заявки'),
            ('description', 'Описание'),
            ('priority', 'Приоритет'),
            ('status', 'Статус'),
            ('created_by', 'Создатель'),
            ('assigned_to', 'Ответственный'),
            ('planned_date', 'Плановая дата'),
            ('completed_date', 'Дата выполнения'),
            ('created_at', 'Дата создания'),
            ('comment', 'Комментарий'),
        ],
        widget=forms.CheckboxSelectMultiple,
        initial=['request_number', 'building', 'priority', 'status', 'created_by', 'assigned_to', 'created_at'],
        required=False,
        label="Отображаемые колонки"
    )
    status = forms.ChoiceField(choices=[('', 'Все')] + ServiceRequest.STATUS_CHOICES, required=False, label="Статус")
    priority = forms.ChoiceField(choices=[('', 'Все')] + ServiceRequest.PRIORITY_CHOICES, required=False, label="Приоритет")
    building = forms.ModelChoiceField(queryset=Building.objects.all(), required=False, label="Здание")
    request_type = forms.ModelChoiceField(queryset=RequestType.objects.filter(is_active=True), required=False, label="Тип заявки")
    assigned_to = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False, label="Ответственный")
    created_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False, label="Создатель")
    room_number = forms.CharField(required=False, label="Номер помещения")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Дата создания от")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Дата создания до")


# Форма для импорта материалов из Excel
class ImportMaterialsForm(forms.Form):
    excel_file = forms.FileField(label="Excel файл", widget=forms.FileInput(attrs={'class': 'form-control'}))


# Форма для добавления/редактирования материалов на складе
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'unit', 'default_price', 'quantity_in_stock']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'default_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'name': 'Наименование',
            'unit': 'Единица измерения',
            'default_price': 'Цена за единицу (₽)',
            'quantity_in_stock': 'Количество на складе',
        }