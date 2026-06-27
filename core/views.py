# core/views.py
# Полная версия: home, unified_dashboard, privacy_policy, CustomLoginView

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from exploitation_app.models import OperationContract, ContractExecution
from buildings.models import Building
from energy.models import Meter, Reading
from energy.utils import get_avg_consumption, is_anomaly

# Импорты для единого дашборда
from exploitation_app.views import get_dashboard_context as get_contracts_context
from requests_app.views import get_dashboard_context as get_requests_context
from energy.views import get_dashboard_context as get_energy_context

# Импорты для кастомной формы входа
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import CustomLoginForm


@login_required
def home(request):
    """Главная страница (дашборд для всех пользователей)"""
    # Фильтрация договоров по роли пользователя
    if hasattr(request.user, 'profile') and request.user.profile.role == 'CONTRACTOR':
        contracts_qs = OperationContract.objects.filter(
            Q(contractor=request.user.username) |
            Q(contractor_contact=request.user.get_full_name())
        )
    else:
        contracts_qs = OperationContract.objects.all()

    # --- Статистика по договорам ---
    total_contracts = contracts_qs.count()
    active_contracts = contracts_qs.filter(status='ACT').count()
    expired_contracts = contracts_qs.filter(status='EXP').count()
    perpetual_contracts = contracts_qs.filter(end_date__isnull=True, status='ACT').count()

    total_amount = contracts_qs.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = ContractExecution.objects.filter(contract__in=contracts_qs).aggregate(total=Sum('paid_amount'))['total'] or 0
    remaining = total_amount - total_paid

    # --- Статусы договоров (с цветом и гарантированным порядком) ---
    status_colors = {
        'ACT': 'success',    # зелёный
        'FPD': 'primary',    # синий
        'TRM': 'warning',    # жёлтый/оранжевый
        'SUS': 'info',       # голубой
        'DRF': 'secondary',  # серый
        'EXP': 'danger',     # красный
    }
    desired_order = ['ACT', 'FPD', 'TRM', 'SUS', 'DRF', 'EXP']

    status_counts = contracts_qs.values('status').annotate(count=Count('id'))
    counts_dict = {item['status']: item['count'] for item in status_counts}

    status_summary = []
    for code in desired_order:
        count = counts_dict.get(code, 0)
        if count > 0:   # показываем только те статусы, которые есть
            status_summary.append({
                'label': dict(OperationContract.ContractStatus.choices).get(code, code),
                'count': count,
                'color': status_colors.get(code, 'dark'),
            })

    # --- Процент оплаты (две версии: для CSS и для отображения) ---
    payment_percent = "0"
    payment_percent_display = "0"
    if total_amount > 0:
        percent_float = (total_paid / total_amount) * 100
        percent_rounded = round(percent_float, 1)
        payment_percent = str(percent_rounded).replace(',', '.')
        payment_percent_display = str(percent_rounded).replace('.', ',')

    total_buildings = Building.objects.count()
    latest_contracts = contracts_qs.select_related('building').order_by('-created_at')[:5]

    # --- Данные для круговой диаграммы по типам договоров ---
    contracts_by_type = {}
    for contract_type in OperationContract.ContractType.choices:
        count = contracts_qs.filter(contract_type=contract_type[0]).count()
        if count > 0:
            contracts_by_type[contract_type[1]] = count

    chart_labels = list(contracts_by_type.keys())
    chart_data = list(contracts_by_type.values())

    # --- Данные энергоучёта ---
    active_meters = Meter.objects.filter(is_active=True).count()
    total_consumption_period = Decimal('0')
    anomalies_period = 0
    today = date.today()
    start_date = date(today.year, 1, 1)
    end_date = today
    readings_period = Reading.objects.filter(date__gte=start_date, date__lte=end_date)
    for reading in readings_period:
        total_consumption_period += reading.total_consumption()
    for meter in Meter.objects.filter(is_active=True):
        avg = get_avg_consumption(meter)
        if avg == 0:
            continue
        readings = meter.reading_set.filter(date__gte=start_date, date__lte=end_date)
        for reading in readings:
            consumption = reading.total_consumption()
            if is_anomaly(consumption, avg, 2.0):
                anomalies_period += 1

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

    # --- Дополнительные показатели для сводки ---
    total_debt = 0
    for contract in contracts_qs:
        if contract.total_amount:
            total_debt += contract.total_amount - contract.total_paid

    overdue_payments = ContractExecution.objects.filter(
        paid_amount=0,
        payment_date__lt=today,
        contract__in=contracts_qs
    ).count()

    # --- Статистика по заявкам ---
    total_requests = 0
    active_requests = 0
    completed_requests = 0
    overdue_requests = 0

    try:
        from requests_app.models import ServiceRequest
        current_year = today.year
        current_month = today.month
        
        # Фильтр по текущему месяцу (для Всего, Активных, Завершённых)
        month_filter = Q(created_at__year=current_year, created_at__month=current_month)

        total_requests = ServiceRequest.objects.filter(month_filter).count()
        active_requests = ServiceRequest.objects.filter(month_filter, status='in_progress').count()
        completed_requests = ServiceRequest.objects.filter(month_filter, status='closed').count()

        # Просроченные заявки (глобально, без фильтра по месяцу)
        try:
            if hasattr(ServiceRequest, 'planned_date'):
                overdue_requests = ServiceRequest.objects.filter(
                    status='in_progress',
                    planned_date__lt=today
                ).count()
        except (AttributeError):
            overdue_requests = 0
    except ImportError:
        pass
    except Exception:
        pass

    context = {
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'expired_contracts': expired_contracts,
        'perpetual_contracts': perpetual_contracts,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'remaining': remaining,
        'payment_percent': payment_percent,
        'payment_percent_display': payment_percent_display,
        'total_buildings': total_buildings,
        'latest_contracts': latest_contracts,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'active_meters': active_meters,
        'total_consumption_period': total_consumption_period,
        'anomalies_period': anomalies_period,
        'consumption_by_type': consumption_list,
        'total_consumption_all': total_consumption_all,
        'period_label': f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}",
        'total_debt': total_debt,
        'overdue_payments': overdue_payments,
        'total_requests': total_requests,
        'active_requests': active_requests,
        'completed_requests': completed_requests,
        'overdue_requests': overdue_requests,
        'status_summary': status_summary,
    }
    return render(request, 'core/home.html', context)


@login_required
def unified_dashboard(request):
    """
    Единый дашборд с вкладками: Договоры, Заявки, Энергетика.
    Фильтры: год и месяц (для договоров используется только год,
             для заявок и энергетики - год и месяц).
    """
    # Получаем параметры фильтрации из GET-запроса
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year:
        try:
            year = int(year)
        except ValueError:
            year = date.today().year
    else:
        year = date.today().year
    
    if month:
        try:
            month = int(month)
            if month < 1 or month > 12:
                month = date.today().month
        except ValueError:
            month = date.today().month
    else:
        month = date.today().month
    
    # Получаем контекст для каждого раздела
    contracts_ctx = get_contracts_context(year=year, request=request)
    requests_ctx = get_requests_context(year=year, month=month)
    energy_ctx = get_energy_context(year=year, month=month)
    
    # Формируем общий контекст
    context = {
        'contracts': contracts_ctx,
        'requests': requests_ctx,
        'energy': energy_ctx,
        'selected_year': year,
        'selected_month': month,
        'available_years': range(date.today().year - 2, date.today().year + 1),
        'available_months': [
            (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
            (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
            (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')
        ],
    }
    return render(request, 'core/unified_dashboard.html', context)


def privacy_policy(request):
    """Страница с политикой обработки персональных данных."""
    return render(request, 'core/privacy_policy.html')


class CustomLoginView(LoginView):
    """
    Представление входа с кастомной формой, требующей согласия на обработку ПД.
    """
    form_class = CustomLoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:home')