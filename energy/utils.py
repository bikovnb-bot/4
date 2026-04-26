from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum
from .models import Reading, UserLog
from users.decorators import is_viewer, is_manager, is_admin

def can_view_all_meters(user):
    """Может ли пользователь видеть все счётчики (администратор, менеджер, наблюдатель)"""
    return is_viewer(user)

def can_edit_all_meters(user):
    """Может ли пользователь редактировать любые счётчики (администратор или менеджер)"""
    return is_manager(user)

def can_assign_owner(user):
    """Может ли пользователь назначать владельца счётчика (только администратор)"""
    return is_admin(user)

def can_view_meter(user, meter):
    """Просмотр конкретного счётчика (все, кто имеет право просмотра)"""
    return can_view_all_meters(user)

def can_edit_meter(user, meter):
    """Редактирование счётчика (администратор или менеджер)"""
    return can_edit_all_meters(user)

def can_delete_meter(user, meter):
    """Удаление счётчика (только администратор)"""
    return is_admin(user)

def can_edit_reading(user, reading):
    """Редактирование показаний (определяется правом редактирования счётчика)"""
    return can_edit_meter(user, reading.meter)

def can_delete_reading(user, reading):
    """Удаление показаний (только администратор)"""
    return can_delete_meter(user, reading.meter)

def can_upload_document(user, meter):
    """Загрузка документов (администратор или менеджер)"""
    return can_edit_meter(user, meter)

def can_delete_document(user, meter):
    """Удаление документов (администратор или менеджер)"""
    return can_edit_meter(user, meter)


# ------------------------------------------------------------
# Функции для проверки аномального потребления
# ------------------------------------------------------------
def get_avg_consumption(meter, months=6):
    """Возвращает среднемесячное потребление за последние months месяцев (без учёта текущего месяца)"""
    today = date.today()
    # Начало периода: первый день месяца, отстоящий на months месяцев назад
    start_date = today.replace(day=1) - timedelta(days=1)
    for _ in range(months - 1):
        start_date = start_date.replace(day=1) - timedelta(days=1)
    start_date = start_date.replace(day=1)
    # Конец периода: последний день предыдущего месяца (не включаем текущий)
    end_date = today.replace(day=1) - timedelta(days=1)
    readings = meter.reading_set.filter(date__gte=start_date, date__lte=end_date)
    if not readings:
        return Decimal('0')
    if meter.is_multi_tariff:
        total = sum(r.total_consumption() for r in readings)
    else:
        total = readings.aggregate(total=Sum('consumption'))['total'] or Decimal('0')
    if total == 0:
        return Decimal('0')
    return total / Decimal(len(readings))

def is_anomaly(consumption, avg_consumption, threshold=2.0):
    """Проверяет аномальность: consumption > avg * threshold"""
    if avg_consumption == 0:
        return False
    # Преобразуем threshold в Decimal для корректного сравнения
    return consumption > avg_consumption * Decimal(str(threshold))


# ------------------------------------------------------------
# Функции для логирования действий пользователей
# ------------------------------------------------------------
def get_client_ip(request):
    """Получает IP-адрес клиента из request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_action(user, action, model_name='', object_id='', details='', request=None):
    """Записывает действие пользователя в лог"""
    ip_address = get_client_ip(request) if request else None
    UserLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        details=details,
        ip_address=ip_address
    )