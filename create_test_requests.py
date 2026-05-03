from datetime import date, timedelta 
from django.utils import timezone 
from requests_app.models import ServiceRequest 
from buildings.models import Building 
from requests_app.models import RequestType 
 
building_id = 2 
request_type_id = 3 
created_by_id = 2 
 
ServiceRequest.objects.filter(request_number__startswith='TEST').delete() 
 
for i in range(1, 16): 
    priority = 'medium' if i %% 3 != 0 else 'high' 
    if i %% 5 == 0: 
        status = 'closed' 
        completed_date = timezone.now() 
        planned_date = date.today() - timedelta(days=5) 
    else: 
        status = 'in_progress' 
        completed_date = None 
        if i %% 4 == 0: 
            planned_date = date.today() - timedelta(days=2) 
        else: 
            planned_date = date.today() + timedelta(days=10) 
    created = date.today() - timedelta(days=i %% 5) 
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
    print(f'Created TEST-{i:03d}, status={status}, created={created}, planned={planned_date}') 
 
print('Total test requests:', ServiceRequest.objects.filter(request_number__startswith='TEST').count()) 
