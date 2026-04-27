from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import ServiceRequest, RequestFile, RequestType, UsedMaterial, Material
from .utils import can_assign_request
from buildings.models import Building


class CustomUserChoiceField(forms.ModelChoiceField):
    """Поле выбора пользователя, отображающее полное имя или username"""
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.username


class ServiceRequestForm(forms.ModelForm):
    assigned_to = CustomUserChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label="Ответственный"
    )

    class Meta:
        model = ServiceRequest
        fields = ['building', 'room_number', 'request_type', 'description', 'priority', 'assigned_to', 'planned_date', 'comment', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'planned_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_assign_request(user):
            self.fields.pop('assigned_to', None)
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

        self.fields['request_type'].queryset = RequestType.objects.filter(is_active=True)


class RequestFileForm(forms.ModelForm):
    class Meta:
        model = RequestFile
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }


# Формсет для материалов (используется при закрытии заявки)
UsedMaterialFormSet = inlineformset_factory(
    ServiceRequest,
    UsedMaterial,
    fields=('name', 'quantity', 'unit', 'price_per_unit'),
    extra=3,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'list': 'materials-list'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'unit': forms.TextInput(attrs={'class': 'form-control'}),
        'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    }
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
    assigned_to = CustomUserChoiceField(queryset=User.objects.filter(is_active=True), required=False, label="Ответственный")
    created_by = CustomUserChoiceField(queryset=User.objects.filter(is_active=True), required=False, label="Создатель")
    room_number = forms.CharField(required=False, label="Номер помещения")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Дата создания от")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Дата создания до")


# Форма для импорта материалов из Excel
class ImportMaterialsForm(forms.Form):
    excel_file = forms.FileField(label="Excel файл")