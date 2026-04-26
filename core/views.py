from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from exploitation_app.models import OperationContract
from buildings.models import Building
from energy.models import Meter, Reading
from energy.utils import get_avg_consumption, is_anomaly

@login_required
def home(request):
    """Главная страница (дашборд для всех пользователей)"""
    # Статистика по договорам
    total_contracts = OperationContract.objects.count()
    active_contracts = OperationContract.objects.filter(status='ACT').count()
    total_amount = OperationContract.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = OperationContract.objects.aggregate(total=Sum('total_paid'))['total'] or 0
    remaining = total_amount - total_paid

    # Количество зданий
    total_buildings = Building.objects.count()

    # Последние договоры (5 штук)
    latest_contracts = OperationContract.objects.select_related('building').order_by('-created_at')[:5]

    # --- Данные из приложения energy с начала текущего года ---
    active_meters = Meter.objects.filter(is_active=True).count()
    total_consumption_period = Decimal('0')
    anomalies_period = 0

    today = date.today()
    start_date = date(today.year, 1, 1)          # 1 января текущего года
    end_date = today

    # Суммарное потребление за период
    readings_period = Reading.objects.filter(date__gte=start_date, date__lte=end_date)
    for reading in readings_period:
        total_consumption_period += reading.total_consumption()

    # Аномалии за период (порог 2.0)
    for meter in Meter.objects.filter(is_active=True):
        avg = get_avg_consumption(meter)
        if avg == 0:
            continue
        readings = meter.reading_set.filter(date__gte=start_date, date__lte=end_date)
        for reading in readings:
            consumption = reading.total_consumption()
            if is_anomaly(consumption, avg, 2.0):
                anomalies_period += 1

    # Потребление по типам ресурсов за период
    consumption_by_type = defaultdict(Decimal)
    for reading in readings_period:
        rt = reading.meter.resource_type
        consumption_by_type[rt] += reading.total_consumption()

    consumption_list = []
    total_consumption_all = Decimal('0')
    for rt, cons in consumption_by_type.items():
        consumption_list.append({
            'name': rt.name,
            'unit': rt.unit,
            'consumption': cons,
        })
        total_consumption_all += cons

    # Формируем подпись для периода (для шаблона)
    period_label = f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"

    context = {
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'remaining': remaining,
        'total_buildings': total_buildings,
        'latest_contracts': latest_contracts,
        # Данные энергоучёта
        'active_meters': active_meters,
        'total_consumption_period': total_consumption_period,
        'anomalies_period': anomalies_period,
        'consumption_by_type': consumption_list,
        'total_consumption_all': total_consumption_all,
        'period_label': period_label,
    }
    return render(request, 'core/home.html', context)