# requests_app/views/dashboard.py
import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from django.db.models.functions import TruncDay, TruncMonth
from django.core.cache import cache

from ..models import ServiceRequest


def get_dashboard_context(year=None, month=None):
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month

    cache_key = f'dashboard_context_{year}_{month}'
    context = cache.get(cache_key)
    if context is not None:
        return context

    qs = ServiceRequest.objects.filter(
        created_at__year=year,
        created_at__month=month
    )

    stats = qs.aggregate(
        total_requests=Count('id'),
        completed_closed=Count('id', filter=Q(status__in=['completed', 'closed'])),
        in_progress=Count('id', filter=Q(status='in_progress')),
        overdue=Count('id', filter=Q(planned_date__lt=date.today(), status__in=['new', 'in_progress', 'suspended'])),
    )
    total_requests = stats['total_requests']
    completed_closed = stats['completed_closed']
    in_progress = stats['in_progress']
    overdue = stats['overdue']
    completion_rate = round(completed_closed / total_requests * 100, 1) if total_requests else 0

    daily_stats = qs.annotate(day=TruncDay('created_at')).values('day').annotate(cnt=Count('id')).order_by('day')
    day_created = {d['day'].day: d['cnt'] for d in daily_stats}
    num_days = calendar.monthrange(year, month)[1]
    days_list = list(range(1, num_days + 1))
    day_created_list = [day_created.get(d, 0) for d in days_list]

    completed_qs = qs.filter(status__in=['completed', 'closed'], completed_date__isnull=False)
    daily_completed = completed_qs.annotate(day=TruncDay('completed_date')).values('day').annotate(cnt=Count('id')).order_by('day')
    day_completed_dict = {d['day'].day: d['cnt'] for d in daily_completed}
    day_completed_list = [day_completed_dict.get(d, 0) for d in days_list]

    year_qs = ServiceRequest.objects.filter(created_at__year=year)
    month_stats = year_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(cnt=Count('id')).order_by('month')
    month_map = {m['month'].month: m['cnt'] for m in month_stats}
    monthly_created = [month_map.get(m, 0) for m in range(1, 13)]
    month_labels = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

    status_counts = qs.values('status').annotate(cnt=Count('id')).order_by('status')
    status_dict = dict(ServiceRequest.STATUS_CHOICES)
    status_labels = [status_dict.get(s['status'], s['status']) for s in status_counts]
    status_data = [s['cnt'] for s in status_counts]

    type_counts = qs.values('request_type__name').annotate(cnt=Count('id')).order_by('-cnt')[:5]
    type_labels = [t['request_type__name'] or 'Без типа' for t in type_counts]
    type_data = [t['cnt'] for t in type_counts]

    priority_counts = qs.values('priority').annotate(cnt=Count('id')).order_by('priority')
    priority_dict = dict(ServiceRequest.PRIORITY_CHOICES)
    priority_labels = [priority_dict.get(p['priority'], p['priority']) for p in priority_counts]
    priority_data = [p['cnt'] for p in priority_counts]

    executor_qs = qs.select_related('assigned_to').prefetch_related('assignees__user')
    executor_counts = {}
    for req in executor_qs:
        if req.assigned_to:
            executor_counts[req.assigned_to] = executor_counts.get(req.assigned_to, 0) + 1
        for assignee in req.assignees.all():
            user_obj = assignee.user
            executor_counts[user_obj] = executor_counts.get(user_obj, 0) + 1
    sorted_executors = sorted(executor_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    assignee_list = [{'name': u.get_full_name() or u.username, 'total': c} for u, c in sorted_executors]

    top_users = [u for u, _ in sorted_executors[:3]]
    assignee_daily = []
    for user_obj in top_users:
        daily_counts = []
        for day in days_list:
            day_requests = qs.filter(created_at__day=day)
            count = day_requests.filter(assigned_to=user_obj).count() + day_requests.filter(assignees__user=user_obj).count()
            daily_counts.append(count)
        assignee_daily.append({
            'label': user_obj.get_full_name() or user_obj.username,
            'data': daily_counts
        })

    completed_reqs = qs.filter(status__in=['completed', 'closed'], completed_date__isnull=False)
    avg_seconds = completed_reqs.aggregate(
        avg=Avg(F('completed_date') - F('created_at'))
    )['avg']
    avg_hours = (avg_seconds.total_seconds() / 3600) if avg_seconds else 0

    # --- ИСПРАВЛЕНИЕ: формируем уникальный список всех исполнителей (основных и дополнительных) ---
    assignee_users = set()
    for req in qs.select_related('assigned_to').prefetch_related('assignees__user'):
        if req.assigned_to:
            assignee_users.add(req.assigned_to)
        for assignee in req.assignees.all():
            assignee_users.add(assignee.user)

    worker_stats = []
    total_completed_closed = completed_closed
    for user_obj in assignee_users:
        completed_count = qs.filter(
            Q(assigned_to=user_obj) | Q(assignees__user=user_obj),
            status__in=['completed', 'closed']
        ).distinct().count()
        total_assigned = qs.filter(
            Q(assigned_to=user_obj) | Q(assignees__user=user_obj)
        ).distinct().count()
        percent = (completed_count / total_completed_closed * 100) if total_completed_closed else 0
        worker_stats.append({
            'name': user_obj.get_full_name() or user_obj.username,
            'completed': completed_count,
            'total_assigned': total_assigned,
            'percent': round(percent, 1)
        })
    worker_stats.sort(key=lambda x: x['completed'], reverse=True)

    today = date.today()
    overdue_requests_qs = ServiceRequest.objects.filter(
        planned_date__lt=today,
        status__in=['new', 'in_progress', 'suspended']
    ).select_related('assigned_to').prefetch_related('assignees__user')
    overdue_count = {}
    for req in overdue_requests_qs:
        if req.assigned_to:
            overdue_count[req.assigned_to] = overdue_count.get(req.assigned_to, 0) + 1
        for a in req.assignees.all():
            overdue_count[a.user] = overdue_count.get(a.user, 0) + 1
    total_overdue = sum(overdue_count.values())
    overdue_assignee_stats = [
        {
            'assignee_name': u.get_full_name() or u.username,
            'assignee_id': u.id,
            'overdue_count': c,
            'percent': round(c / total_overdue * 100, 1) if total_overdue else 0
        }
        for u, c in sorted(overdue_count.items(), key=lambda x: x[1], reverse=True)
    ]

    month_names_ru = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    available_months = [(m, month_names_ru[m]) for m in range(1, 13)]
    current_month_name = month_names_ru[month]

    context = {
        'selected_year': year,
        'selected_month': month,
        'current_month_name': current_month_name,
        'available_years': range(date.today().year - 2, date.today().year + 1),
        'available_months': available_months,
        'total_requests': total_requests,
        'completed_closed': completed_closed,
        'in_progress': in_progress,
        'overdue': overdue,
        'completion_rate': completion_rate,
        'day_labels': days_list,
        'day_created': day_created_list,
        'day_completed': day_completed_list,
        'month_labels': month_labels,
        'monthly_created': monthly_created,
        'status_labels': status_labels,
        'status_data': status_data,
        'type_labels': type_labels,
        'type_data': type_data,
        'priority_labels': priority_labels,
        'priority_data': priority_data,
        'assignee_list': assignee_list,
        'assignee_daily': assignee_daily,
        'avg_completion_hours': round(avg_hours, 1),
        'worker_stats': worker_stats,
        'overdue_assignee_stats': overdue_assignee_stats,
    }
    cache.set(cache_key, context, 60*5)  # 5 минут
    return context


@login_required
def request_dashboard(request):
    from users.models import UserRole
    user = request.user
    role = user.profile.role if hasattr(user, 'profile') else None
    if role not in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
        messages.error(request, 'У вас нет доступа к дашборду.')
        return redirect('requests_app:request_list')

    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    context = get_dashboard_context(year, month)
    context['all_widgets'] = []
    context['visible_widgets'] = []
    return render(request, 'requests_app/dashboard.html', context)