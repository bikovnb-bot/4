# core/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class CustomLoginForm(AuthenticationForm):
    """
    Форма входа с обязательным согласием на обработку персональных данных.
    """
    agree_to_policy = forms.BooleanField(
        label="Я ознакомлен и согласен с политикой обработки персональных данных",
        required=True,
        error_messages={
            'required': 'Для входа необходимо согласие на обработку персональных данных.'
        },
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите логин',
            'autofocus': True
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
        # Убираем стандартные метки, чтобы использовать свои в шаблоне
        self.fields['username'].label = 'Имя пользователя'
        self.fields['password'].label = 'Пароль'