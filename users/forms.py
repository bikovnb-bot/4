# users/forms.py

from django import forms
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.password_validation import validate_password
from .models import UserRole, Profile

# ------------------------------------------------------------
# Форма фильтрации списка пользователей
# ------------------------------------------------------------
class UserFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск...'}))
    role = forms.ChoiceField(required=False, choices=[('', 'Все роли')] + list(UserRole.choices), widget=forms.Select(attrs={'class': 'form-select'}))
    is_active = forms.ChoiceField(required=False, choices=[('', 'Все'), ('active', 'Активные'), ('inactive', 'Неактивные')], widget=forms.Select(attrs={'class': 'form-select'}))

# ------------------------------------------------------------
# Форма смены пароля (для администратора, без старого пароля)
# ------------------------------------------------------------
class ChangePasswordForm(forms.Form):
    password = forms.CharField(label='Новый пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}), validators=[validate_password])
    password_confirm = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data

# ------------------------------------------------------------
# Форма профиля (роль, телефон, должность)
# ------------------------------------------------------------
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role', 'phone', 'position']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
        }

# ------------------------------------------------------------
# Форма создания пользователя (только поля User)
# ------------------------------------------------------------
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), validators=[validate_password])
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.set_password(self.cleaned_data['password'])
            user.save()
            self.save_m2m()  # сохраняет группы
        return user

# ------------------------------------------------------------
# Форма редактирования пользователя
# ------------------------------------------------------------
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m()
        return user

# ------------------------------------------------------------
# Форма редактирования профиля (самим пользователем)
# ------------------------------------------------------------
class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label='Имя', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, label='Фамилия', widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=False, label='Телефон', widget=forms.TextInput(attrs={'class': 'form-control'}))
    position = forms.CharField(max_length=100, required=False, label='Должность', widget=forms.TextInput(attrs={'class': 'form-control'}))
    avatar = forms.ImageField(required=False, label='Аватар', widget=forms.FileInput(attrs={'class': 'form-control'}))

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

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Аватар не более 5 МБ')
            if not avatar.content_type in ['image/jpeg', 'image/png', 'image/gif']:
                raise forms.ValidationError('Только JPEG, PNG, GIF')
        return avatar

# ------------------------------------------------------------
# Форма управления группами
# ------------------------------------------------------------
class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 15}),
        required=False,
        label='Права'
    )
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}