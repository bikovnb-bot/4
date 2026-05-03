from datetime import date, timedelta
from django.utils import timezone
from requests_app.models import ServiceRequest
from buildings.models import Building
from requests_app.models import RequestType

# ID объектов (скорректируйте при необходимости)
building_id = 2
request_type_id = 3
created_by_id = 2

# Удаляем старые тестовые заявки
deleted, _ = ServiceRequest.objects.filter(request_number__startswith='TEST').delete()
print(f"Удалено старых тестовых заявок: {deleted}")

for i in range(1, 16):
    priority = 'medium' if i % 3 != 0 else 'high'
    if i % 5 == 0:
        status = 'closed'
        completed_date = timezone.now()
        planned_date = date.today() - timedelta(days=5)
    else:
        status = 'in_progress'
        completed_date = None
        if i % 4 == 0:
            planned_date = date.today() - timedelta(days=2)   # просрочено
        else:
            planned_date = date.today() + timedelta(days=10)  # не просрочено

    created = date.today() - timedelta(days=i % 5)

    ServiceRequest.objects.create(
        request_number=f'TEST-{i:03d}',
        building_id=building_id,
        room_number=f'Room-{i}',
        request_type_id=request_type_id,
        description=f'Тестовая заявка {i}',
        priority=priority,
        status=status,
        track_time=True,
        created_by_id=created_by_id,
        created_at=created,
        planned_date=planned_date,
        completed_date=completed_date,
        comment=''
    )
    print(f'Создана заявка TEST-{i:03d}, статус={status}, создана={created}, срок={planned_date}')

print(f'\n✅ Всего создано тестовых заявок: {ServiceRequest.objects.filter(request_number__startswith="TEST").count()}')