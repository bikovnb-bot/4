# users/forms.py

from django import forms
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.password_validation import validate_password
from .models import UserRole, Profile


class UserFilterForm(forms.Form):
    """Форма фильтрации списка пользователей"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по логину, имени, email...'})
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'Все роли')] + list(UserRole.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('active', 'Активные'), ('inactive', 'Неактивные')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ChangePasswordForm(forms.Form):
    """Форма смены пароля администратором или пользователем"""
    password = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите новый пароль'}),
        validators=[validate_password]
    )
    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите новый пароль'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data


class UserCreateForm(forms.ModelForm):
    """Форма создания нового пользователя (администратором)"""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        validators=[validate_password]
    )
    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=UserRole.choices,
        label='Роль',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Телефон',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    position = forms.CharField(
        max_length=100,
        required=False,
        label='Должность',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='Активен',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Группы',
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data


class UserEditForm(forms.ModelForm):
    """Форма редактирования пользователя (администратором)"""
    role = forms.ChoiceField(
        choices=UserRole.choices,
        label='Роль',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Телефон',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    position = forms.CharField(
        max_length=100,
        required=False,
        label='Должность',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False,
        label='Активен',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Группы',
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups', 'is_active']  # добавили is_active
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class ProfileEditForm(forms.ModelForm):
    """Форма редактирования профиля пользователем (самостоятельно)"""
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='Имя',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Фамилия',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Телефон',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    position = forms.CharField(
        max_length=100,
        required=False,
        label='Должность',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    avatar = forms.ImageField(
        required=False,
        label='Аватар',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['phone'].initial = profile.phone
            self.fields['position'].initial = profile.position
            if profile.avatar:
                self.fields['avatar'].initial = profile.avatar

    def save(self, commit=True):
        user = super().save(commit=commit)
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.phone = self.cleaned_data.get('phone', '')
            profile.position = self.cleaned_data.get('position', '')
            if self.cleaned_data.get('avatar'):
                profile.avatar = self.cleaned_data['avatar']
            profile.save()
        return user


class GroupForm(forms.ModelForm):
    """Форма для управления группами"""
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 15}),
        required=False,
        label='Права'
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }