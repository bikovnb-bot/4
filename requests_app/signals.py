from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import ServiceRequest

@receiver(pre_save, sender=ServiceRequest)
def handle_status_change(sender, instance, **kwargs):
    if instance.pk:
        old_status = ServiceRequest.objects.get(pk=instance.pk).status
        new_status = instance.status
        # Если статус меняется с 'closed' на что-то другое – возвращаем материалы
        if old_status == 'closed' and new_status != 'closed':
            instance.return_materials_to_stock()