from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Reading, ZoneReading

@receiver([post_save, post_delete], sender=Reading)
@receiver([post_save, post_delete], sender=ZoneReading)
def recalc_meter_consumption(sender, instance, **kwargs):
    # Если объект помечен как сохраняемый внутри recalc_consumption – пропускаем
    if hasattr(instance, '_skip_recalc') and instance._skip_recalc:
        return
    # Получаем счётчик
    if isinstance(instance, ZoneReading):
        meter = instance.reading.meter
    else:
        meter = instance.meter
    # Если рекурсивный вызов уже идёт – пропускаем
    if hasattr(meter, '_recalc_running') and meter._recalc_running:
        return
    meter.recalc_consumption()