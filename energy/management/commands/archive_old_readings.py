from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from energy.models import Reading, ZoneReading, ArchivedReading, ArchivedZoneReading

class Command(BaseCommand):
    help = 'Архивирует показания старше 2 лет'

    def handle(self, *args, **options):
        cutoff_date = timezone.now().date() - timedelta(days=730)
        old_readings = Reading.objects.filter(date__lt=cutoff_date)
        count = 0
        for reading in old_readings:
            # Создаём архивную запись
            archived = ArchivedReading.objects.create(
                meter=reading.meter,
                date=reading.date,
                value=reading.value,
                consumption=reading.consumption
            )
            # Копируем зоны
            for zr in reading.zone_readings.all():
                ArchivedZoneReading.objects.create(
                    archived_reading=archived,
                    tariff_component=zr.tariff_component,
                    value=zr.value,
                    consumption=zr.consumption
                )
            reading.delete()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Архивировано {count} показаний'))