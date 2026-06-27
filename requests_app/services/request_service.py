# requests_app/services/request_service.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import (
    ServiceRequest, RequestHistory, RequestFile, UsedMaterial,
    Material, RequestAssignee, MaterialTransaction
)


class RequestService:
    """Сервис для управления заявками."""

    @staticmethod
    def add_history_entry(request, user, action, old_value=None, new_value=None):
        """Создаёт запись в истории заявки."""
        RequestHistory.objects.create(
            request=request,
            user=user,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )

    @staticmethod
    def create_request(data, created_by, files=None):
        request = ServiceRequest(**data)
        request.created_by = created_by
        request.status = 'new'
        if not request.created_at:
            request.created_at = timezone.now()
        request.save()
        if files:
            for f in files:
                RequestFile.objects.create(
                    request=request,
                    file=f,
                    uploaded_by=created_by,
                    description=''
                )
        return request

    @staticmethod
    def update_request(request, data, files=None, delete_file_ids=None):
        for attr, value in data.items():
            setattr(request, attr, value)
        request.save()
        if delete_file_ids:
            for file_id in delete_file_ids:
                try:
                    file_obj = RequestFile.objects.get(id=file_id, request=request)
                    if file_obj.file:
                        file_obj.file.delete()
                    file_obj.delete()
                except RequestFile.DoesNotExist:
                    pass
        if files:
            for f in files:
                RequestFile.objects.create(
                    request=request,
                    file=f,
                    uploaded_by=request.created_by,
                    description=''
                )
        return request

    @staticmethod
    def assign_executor(request, assigned_to_id, user):
        if not assigned_to_id:
            return False, 'Выберите исполнителя'
        try:
            assigned_to = User.objects.get(pk=assigned_to_id)
        except User.DoesNotExist:
            return False, 'Пользователь не найден'
        request.assigned_to = assigned_to
        if request.status == 'new':
            request.status = 'in_progress'
        request.save()
        RequestService.add_history_entry(
            request=request,
            user=user,
            action=f'Назначен исполнитель: {assigned_to.get_full_name() or assigned_to.username}'
        )
        return True, 'Исполнитель назначен'

    @staticmethod
    def mark_completed(request, user, time_spent=None):
        if request.status != 'in_progress':
            return False, 'Заявка не в работе'
        request.status = 'completed'
        request.completed_date = timezone.now()
        if time_spent and time_spent.isdigit():
            request.time_spent = int(time_spent)
        request.save()
        RequestService.add_history_entry(
            request=request,
            user=user,
            action='Заявка отмечена как выполненная' + (f' (время: {time_spent} мин)' if time_spent else '')
        )
        return True, 'Заявка выполнена'

    @staticmethod
    def suspend_request(request, user, reason):
        if not reason:
            return False, 'Укажите причину приостановки'
        request.status = 'suspended'
        request.suspension_reason = reason
        request.save()
        RequestService.add_history_entry(
            request=request,
            user=user,
            action=f'Заявка приостановлена. Причина: {reason}'
        )
        return True, 'Заявка приостановлена'

    @staticmethod
    def resume_request(request, user):
        request.status = 'in_progress'
        request.save()
        RequestService.add_history_entry(
            request=request,
            user=user,
            action='Заявка возобновлена'
        )
        return True, 'Заявка возобновлена'

    @staticmethod
    def close_request(request, user, materials_data):
        if request.status != 'completed':
            return False, 'Заявка должна быть в статусе "Выполнена" для закрытия.'

        with transaction.atomic():
            materials_used = False
            for item in materials_data:
                material_id = item.get('material_id')
                quantity = item.get('quantity')
                unit = item.get('unit')
                price = item.get('price_per_unit')
                if not material_id or not quantity:
                    continue
                try:
                    qty = Decimal(str(quantity).replace(',', '.'))
                    if qty <= 0:
                        continue
                except (ValueError, TypeError):
                    continue
                try:
                    material = Material.objects.get(pk=int(material_id))
                except Material.DoesNotExist:
                    return False, f'Материал с ID {material_id} не найден.'
                if material.quantity_in_stock < qty:
                    return False, (
                        f'Недостаточно материала "{material.name}" на складе '
                        f'(доступно: {material.quantity_in_stock} {material.unit})'
                    )
                UsedMaterial.objects.create(
                    request=request,
                    material=material,
                    name=material.name,
                    quantity=qty,
                    unit=unit,
                    price_per_unit=Decimal(price) if price else Decimal(0)
                )
                material.quantity_in_stock -= qty
                material.save()
                MaterialTransaction.objects.create(
                    material=material,
                    request=request,
                    quantity=qty,
                    transaction_type='out',
                    comment=f'Списание при закрытии заявки {request.request_number}'
                )
                materials_used = True
            request.status = 'closed'
            request.save()
            RequestService.add_history_entry(
                request=request,
                user=user,
                action='Заявка закрыта' + (' (с материалами)' if materials_used else ' (без материалов)')
            )
            return True, 'Заявка закрыта'

    @staticmethod
    def add_assignee(request, user, assignee_id):
        try:
            assignee = User.objects.get(pk=assignee_id)
        except User.DoesNotExist:
            return False, 'Пользователь не найден'
        obj, created = RequestAssignee.objects.get_or_create(request=request, user=assignee)
        if created:
            RequestService.add_history_entry(
                request=request,
                user=user,
                action=f'Добавлен исполнитель: {assignee.get_full_name() or assignee.username}'
            )
            return True, f'Исполнитель {assignee.get_full_name() or assignee.username} добавлен.'
        return False, 'Этот исполнитель уже назначен'

    @staticmethod
    def remove_assignee(request, user, assignee_id):
        try:
            assignee = RequestAssignee.objects.get(request=request, user_id=assignee_id)
        except RequestAssignee.DoesNotExist:
            return False, 'Исполнитель не найден'
        assignee_name = assignee.user.get_full_name() or assignee.user.username
        assignee.delete()
        RequestService.add_history_entry(
            request=request,
            user=user,
            action=f'Удалён исполнитель: {assignee_name}'
        )
        return True, f'Исполнитель {assignee_name} удалён.'

    @staticmethod
    def delete_request(request, user):
        RequestService.add_history_entry(
            request=request,
            user=user,
            action='Заявка удалена'
        )
        request.delete()
        return True, f'Заявка {request.request_number} удалена.'