# requests_app/utils.py
import requests

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings
from users.decorators import is_viewer, is_manager, is_admin


def can_view_all_requests(user):
    """Может ли пользователь просматривать все заявки?"""
    return is_viewer(user)  # все авторизованные пользователи могут видеть (с фильтрами)


def can_edit_any_request(user):
    """Может ли пользователь редактировать любую заявку?"""
    return is_manager(user)


def can_delete_request(user):
    """Может ли пользователь удалять заявки?"""
    return is_admin(user)


def can_assign_request(user):
    """Может ли пользователь назначать исполнителей?"""
    return is_manager(user) or is_admin(user)


def is_assignee_or_creator(user, request_obj):
    """Является ли пользователь исполнителем или создателем заявки?"""
    return request_obj.assigned_to == user or request_obj.created_by == user


# requests_app/utils.py

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings


def rate_limit(limit=None, window=None):
    """
    Декоратор ограничения количества запросов с одного IP.
    
    Args:
        limit (int): Максимальное количество запросов за период.
                     Если None, берется из settings.RATE_LIMIT_REQUESTS.
        window (int): Период в секундах.
                     Если None, берется из settings.RATE_LIMIT_WINDOW.
    """
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            # Берём параметры из настроек, если не переданы явно
            _limit = limit if limit is not None else getattr(settings, 'RATE_LIMIT_REQUESTS', 10)
            _window = window if window is not None else getattr(settings, 'RATE_LIMIT_WINDOW', 3600)

            # Определяем реальный IP (учитываем прокси)
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip:
                ip = ip.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

            cache_key = f'rate_limit_public_request_{ip}'
            count = cache.get(cache_key, 0)

            if count >= _limit:
                return HttpResponseForbidden(
                    "Слишком много заявок. Попробуйте позже. / Too many requests. Please try later."
                )

            cache.set(cache_key, count + 1, _window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

def send_telegram_notification(message):
    """Отправляет сообщение в Telegram."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=5)
        response.raise_for_status()
    except Exception as e:
        # Не прерываем выполнение, но можно залогировать
        print(f"Telegram error: {e}")
