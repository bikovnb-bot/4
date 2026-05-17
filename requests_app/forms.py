# requests_app/forms.py

import random
from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import ServiceRequest, RequestFile, RequestType, UsedMaterial, Material
from buildings.models import Building


class ServiceRequestForm(forms.ModelForm):
    """Упрощённая форма создания/редактирования заявки"""
    planned_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control datepicker', 'placeholder': 'дд.мм.гггг'}),
        label='Плановая дата выполнения',
        input_formats=['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y']
    )
    time_spent = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
        label='Затраченное время (минуты)'
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
            'time_spent',
        ]
        widgets = {
            'building': forms.Select(attrs={'class': 'form-select'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 117'}),
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Опишите проблему...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'time_spent': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
        }
        labels = {
            'building': 'Здание',
            'room_number': 'Номер помещения',
            'request_type': 'Тип заявки',
            'description': 'Описание',
            'priority': 'Приоритет',
            'planned_date': 'Плановая дата',
            'time_spent': 'Затраченное время (минуты)',
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_type'].queryset = RequestType.objects.filter(is_active=True)


class RequestFileForm(forms.ModelForm):
    """Форма для загрузки файлов к заявке"""
    class Meta:
        model = RequestFile
        fields = ['file', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Описание (необязательно)'}),
        }


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


# Форма для настраиваемого отчёта
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


# Форма для публичной заявки (без авторизации)
class PublicRequestForm(forms.ModelForm):
    building = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Здание / Building"
    )
    room_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Номер помещения / Room number",
        required=True
    )
    request_type = forms.ModelChoiceField(
        queryset=RequestType.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Тип заявки / Request type"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label="Описание / Description"
    )
    contact_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Контактное лицо / Contact person"
    )
    contact_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Телефон / Phone"
    )
    honey = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'value': ''}),
        label=""
    )
    captcha_num1 = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    captcha_num2 = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    captcha_operator = forms.CharField(widget=forms.HiddenInput(), required=False)
    captcha_answer = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '?'}),
        label="Решите пример:"
    )

    class Meta:
        model = ServiceRequest
        fields = ['building', 'room_number', 'request_type', 'description',
                  'contact_name', 'contact_phone']

    def __init__(self, *args, lang='ru', **kwargs):
        super().__init__(*args, **kwargs)
        self.lang = lang

        # Определяем, откуда брать значения для капчи
        # Если форма привязана к данным (POST), используем self.data
        # иначе генерируем новые числа через _generate_captcha
        if self.is_bound:
            # Берём числа из отправленных данных
            num1 = self.data.get('captcha_num1')
            num2 = self.data.get('captcha_num2')
            op = self.data.get('captcha_operator')
            if num1 is not None and num2 is not None and op:
                # Формируем метку вопроса
                if self.lang == 'en':
                    self.fields['captcha_answer'].label = f"How much is {num1} {op} {num2}?"
                else:
                    self.fields['captcha_answer'].label = f"Сколько будет {num1} {op} {num2}?"
            else:
                # Если данных нет – генерируем новые числа
                self._generate_captcha()
        else:
            # GET-запрос: генерируем свежие числа
            self._generate_captcha()

        # --- Остальная локализация полей (русский / английский) ---
        # Словари переводов для зданий и типов заявок (только для английского)
        building_translations = {
            'Студенческое общежитие': 'Student dormitories',
            'Территория': 'Territory',
            'Учебный корпус': 'Academic building',
        }
        type_translations = {
            'Перемещение мебели/оборудования': 'Moving furniture/equipment',
            'Плотницкие работы': 'Carpentry work',
            'Прочие': 'Others',
            'Сантехника': 'Plumbing',
            'Электроснабжение': 'Electricity',
        }

        if self.lang == 'en':
            # Английские метки и плейсхолдеры
            self.fields['building'].label = "Building"
            self.fields['room_number'].label = "Room number"
            self.fields['room_number'].widget.attrs['placeholder'] = "e.g., 117"
            self.fields['request_type'].label = "Request type"
            self.fields['description'].label = "Description"
            self.fields['description'].widget.attrs['placeholder'] = "Describe the problem..."
            self.fields['contact_name'].label = "Contact person"
            self.fields['contact_name'].widget.attrs['placeholder'] = "Ivan Ivanov"
            self.fields['contact_phone'].label = "Phone"
            self.fields['contact_phone'].widget.attrs['placeholder'] = "+7 (XXX) XXX-XX-XX"

            # Переопределяем choices для building и request_type (перевод названий)
            building_choices = []
            for b in Building.objects.all():
                ru_name = str(b)
                en_name = building_translations.get(ru_name, self._transliterate(ru_name))
                building_choices.append((b.id, en_name))
            self.fields['building'].choices = building_choices

            type_choices = []
            for t in RequestType.objects.filter(is_active=True):
                ru_type_name = t.name
                en_name = type_translations.get(ru_type_name, self._transliterate(ru_type_name))
                type_choices.append((t.id, en_name))
            self.fields['request_type'].choices = type_choices
        else:
            # Русские метки
            self.fields['building'].label = "Здание"
            self.fields['room_number'].label = "Номер помещения"
            self.fields['room_number'].widget.attrs['placeholder'] = "Например, 117"
            self.fields['request_type'].label = "Тип заявки"
            self.fields['description'].label = "Описание"
            self.fields['description'].widget.attrs['placeholder'] = "Опишите проблему..."
            self.fields['contact_name'].label = "Контактное лицо"
            self.fields['contact_name'].widget.attrs['placeholder'] = "Иван Иванов"
            self.fields['contact_phone'].label = "Телефон"
            self.fields['contact_phone'].widget.attrs['placeholder'] = "+7 (XXX) XXX-XX-XX"

    def _generate_captcha(self):
        """Генерирует случайное арифметическое выражение и сохраняет в initial."""
        operators = ['+', '-', '*']
        op = random.choice(operators)
        if op == '+':
            a = random.randint(1, 20)
            b = random.randint(1, 20)
        elif op == '-':
            a = random.randint(5, 20)
            b = random.randint(1, a)
        else:  # '*'
            a = random.randint(1, 10)
            b = random.randint(1, 10)
        self.initial['captcha_num1'] = a
        self.initial['captcha_num2'] = b
        self.initial['captcha_operator'] = op
        if self.lang == 'en':
            self.fields['captcha_answer'].label = f"How much is {a} {op} {b}?"
        else:
            self.fields['captcha_answer'].label = f"Сколько будет {a} {op} {b}?"

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get('captcha_answer')
        num1 = self.cleaned_data.get('captcha_num1')
        num2 = self.cleaned_data.get('captcha_num2')
        op = self.cleaned_data.get('captcha_operator')
        if None in [num1, num2, op]:
            raise forms.ValidationError("Ошибка капчи. Пожалуйста, обновите страницу.")
        if op == '+':
            expected = num1 + num2
        elif op == '-':
            expected = num1 - num2
        elif op == '*':
            expected = num1 * num2
        else:
            expected = None
        if expected is None or answer != expected:
            if self.lang == 'en':
                raise forms.ValidationError("Invalid answer. Please try again.")
            else:
                raise forms.ValidationError("Неверный ответ. Попробуйте ещё раз.")
        return answer

    def clean_honey(self):
        if self.cleaned_data.get('honey'):
            raise forms.ValidationError("Spam detected.")
        return ''

    def _transliterate(self, text):
        """Транслитерация кириллицы в латиницу (только для английской версии)."""
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        }
        result = ''
        for ch in text.lower():
            if ch in translit_map:
                result += translit_map[ch]
            elif ch.isalpha() and ch not in translit_map:
                result += ch
            else:
                result += ch
        return result.capitalize()