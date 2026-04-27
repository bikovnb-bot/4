from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from decimal import Decimal
import json
from django.core.paginator import Paginator
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from django.db.models import Q

from .models import ServiceRequest, RequestFile, UsedMaterial, Material
from .forms import ServiceRequestForm, RequestFileForm, ReportForm
from .utils import can_assign_request, can_view_all_requests
from users.decorators import manager_required, viewer_required


# ------------------------------------------------------------
# Список заявок
# ------------------------------------------------------------
class RequestListView(LoginRequiredMixin, ListView):
    model = ServiceRequest
    template_name = 'requests_app/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        qs = ServiceRequest.objects.select_related('building', 'created_by', 'assigned_to', 'request_type')
        if not can_view_all_requests(self.request.user):
            qs = qs.filter(created_by=self.request.user)
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        building_id = self.request.GET.get('building')
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if building_id:
            qs = qs.filter(building_id=building_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from buildings.models import Building
        context['buildings'] = Building.objects.all()
        context['status_choices'] = ServiceRequest.STATUS_CHOICES
        context['priority_choices'] = ServiceRequest.PRIORITY_CHOICES
        context['can_edit'] = can_assign_request(self.request.user)
        context['can_delete'] = self.request.user.is_superuser
        return context


# ------------------------------------------------------------
# Детали заявки
# ------------------------------------------------------------
class RequestDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = ServiceRequest
    template_name = 'requests_app/request_detail.html'
    context_object_name = 'request_obj'

    def test_func(self):
        request_obj = self.get_object()
        if can_view_all_requests(self.request.user):
            return True
        return request_obj.created_by == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = can_assign_request(self.request.user)
        context['can_delete'] = self.request.user.is_superuser
        return context


# ------------------------------------------------------------
# Создание заявки
# ------------------------------------------------------------
class RequestCreateView(LoginRequiredMixin, CreateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'requests_app/request_form.html'
    success_url = reverse_lazy('requests_app:request_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        files = self.request.FILES.getlist('files')
        for f in files:
            RequestFile.objects.create(request=self.object, file=f)
        messages.success(self.request, "Заявка создана")
        return response


# ------------------------------------------------------------
# Редактирование заявки
# ------------------------------------------------------------
class RequestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'requests_app/request_form.html'
    success_url = reverse_lazy('requests_app:request_list')

    def test_func(self):
        if can_assign_request(self.request.user):
            return True
        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_status = ServiceRequest.objects.get(pk=self.object.pk).status
        response = super().form_valid(form)
        if old_status == 'closed' and form.instance.status != 'closed':
            messages.info(self.request, "Материалы возвращены на склад.")
        else:
            messages.success(self.request, "Заявка обновлена")
        return response


# ------------------------------------------------------------
# Удаление заявки
# ------------------------------------------------------------
class RequestDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ServiceRequest
    template_name = 'requests_app/request_confirm_delete.html'
    success_url = reverse_lazy('requests_app:request_list')

    def test_func(self):
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Заявка удалена")
        return super().delete(request, *args, **kwargs)


# ------------------------------------------------------------
# Закрытие заявки (с материалами и проверкой остатков)
# ------------------------------------------------------------
@login_required
@manager_required
def close_request(request, pk):
    request_obj = get_object_or_404(ServiceRequest, pk=pk)
    if request_obj.status == 'closed':
        messages.warning(request, "Заявка уже закрыта.")
        return redirect('requests_app:request_detail', pk=pk)

    if request.method == 'POST':
        request_obj.used_materials.all().delete()
        names = request.POST.getlist('material_name[]')
        quantities = request.POST.getlist('material_quantity[]')
        units = request.POST.getlist('material_unit[]')
        prices = request.POST.getlist('material_price[]')
        errors = []
        materials_to_use = []

        for i in range(len(names)):
            name = names[i].strip()
            if not name:
                continue
            try:
                qty = Decimal(quantities[i]) if quantities[i] else Decimal('0')
                price = Decimal(prices[i]) if prices[i] else Decimal('0')
                unit = units[i].strip()
                if qty <= 0:
                    errors.append(f"В строке {i+1}: количество должно быть положительным")
                    continue
                if price < 0:
                    errors.append(f"В строке {i+1}: цена не может быть отрицательной")
                    continue
                material = Material.objects.filter(name=name).first()
                if material:
                    if material.quantity_in_stock < qty:
                        errors.append(f"Недостаточно материала '{name}' на складе (остаток: {material.quantity_in_stock} {material.unit}, требуется {qty} {unit})")
                        continue
                    materials_to_use.append((material, qty))
            except Exception as e:
                errors.append(f"Ошибка в строке {i+1}: {str(e)}")

        if errors:
            messages.error(request, "Исправьте ошибки:<br>" + "<br>".join(errors[:5]))
            return redirect('requests_app:request_close', pk=pk)

        for i in range(len(names)):
            name = names[i].strip()
            if not name:
                continue
            qty = Decimal(quantities[i]) if quantities[i] else Decimal('0')
            price = Decimal(prices[i]) if prices[i] else Decimal('0')
            unit = units[i].strip()
            UsedMaterial.objects.create(
                request=request_obj,
                name=name,
                quantity=qty,
                unit=unit,
                price_per_unit=price
            )
            material = Material.objects.filter(name=name).first()
            if material:
                material.quantity_in_stock -= qty
                material.save()

        request_obj.status = 'closed'
        request_obj.completed_date = timezone.now()
        request_obj.save()
        messages.success(request, f"Заявка {request_obj.request_number} закрыта, материалы списаны.")
        return redirect('requests_app:request_detail', pk=pk)

    materials = Material.objects.all().order_by('name')
    materials_data = [
        {
            'name': m.name,
            'unit': m.unit,
            'price': float(m.default_price),
            'stock': float(m.quantity_in_stock)
        } for m in materials
    ]
    context = {
        'request_obj': request_obj,
        'materials': materials,
        'materials_json': json.dumps(materials_data, ensure_ascii=False),
    }
    return render(request, 'requests_app/close_request.html', context)


# ------------------------------------------------------------
# Удаление прикреплённого файла
# ------------------------------------------------------------
@login_required
def delete_request_file(request, pk):
    file_obj = get_object_or_404(RequestFile, pk=pk)
    request_obj = file_obj.request
    if can_assign_request(request.user) or request_obj.created_by == request.user:
        file_obj.delete()
        messages.success(request, "Файл удалён.")
    else:
        messages.error(request, "Нет прав на удаление файла.")
    return redirect('requests_app:request_detail', pk=request_obj.pk)


# ------------------------------------------------------------
# Просмотр материалов на складе
# ------------------------------------------------------------
@login_required
@viewer_required
def material_stock(request):
    materials = Material.objects.all().order_by('name')
    search = request.GET.get('search')
    if search:
        materials = materials.filter(name__icontains=search)
    paginator = Paginator(materials, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'materials': page_obj,
        'search': search,
    }
    return render(request, 'requests_app/material_stock.html', context)


# ------------------------------------------------------------
# Экспорт материалов на складе в Excel
# ------------------------------------------------------------
@login_required
@viewer_required
def material_stock_export(request):
    materials = Material.objects.all().order_by('name')
    search = request.GET.get('search')
    if search:
        materials = materials.filter(name__icontains=search)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Материалы на складе"
    headers = ['№', 'Наименование', 'Ед. изм.', 'Цена за ед. (₽)', 'Остаток']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row, material in enumerate(materials, 2):
        ws.cell(row=row, column=1, value=row-1)
        ws.cell(row=row, column=2, value=material.name)
        ws.cell(row=row, column=3, value=material.unit)
        ws.cell(row=row, column=4, value=float(material.default_price))
        ws.cell(row=row, column=5, value=float(material.quantity_in_stock))
    for col in range(1, 6):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 25
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="material_stock.xlsx"'
    wb.save(response)
    return response


# ------------------------------------------------------------
# Настраиваемый отчёт по заявкам
# ------------------------------------------------------------
@login_required
@viewer_required
def custom_report(request):
    form = ReportForm(request.GET or None)
    qs = ServiceRequest.objects.select_related('building', 'created_by', 'assigned_to', 'request_type').all()
    
    if form.is_valid():
        if form.cleaned_data.get('status'):
            qs = qs.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('priority'):
            qs = qs.filter(priority=form.cleaned_data['priority'])
        if form.cleaned_data.get('building'):
            qs = qs.filter(building=form.cleaned_data['building'])
        if form.cleaned_data.get('request_type'):
            qs = qs.filter(request_type=form.cleaned_data['request_type'])
        if form.cleaned_data.get('assigned_to'):
            qs = qs.filter(assigned_to=form.cleaned_data['assigned_to'])
        if form.cleaned_data.get('created_by'):
            qs = qs.filter(created_by=form.cleaned_data['created_by'])
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(created_at__date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(created_at__date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('room_number'):
            qs = qs.filter(room_number__icontains=form.cleaned_data['room_number'])
    
    columns = form.cleaned_data.get('columns') if form.is_valid() else ['request_number', 'building', 'priority', 'status', 'created_by', 'assigned_to', 'created_at']
    
    data = []
    for req in qs:
        row = {}
        for col in columns:
            if col == 'request_number':
                row[col] = req.request_number
            elif col == 'building':
                row[col] = str(req.building)
            elif col == 'room_number':
                row[col] = req.room_number
            elif col == 'request_type':
                row[col] = req.request_type.name
            elif col == 'description':
                row[col] = req.description[:100] + '…' if len(req.description) > 100 else req.description
            elif col == 'priority':
                row[col] = req.get_priority_display()
            elif col == 'status':
                row[col] = req.get_status_display()
            elif col == 'created_by':
                row[col] = req.created_by.get_full_name() or req.created_by.username if req.created_by else '—'
            elif col == 'assigned_to':
                row[col] = req.assigned_to.get_full_name() or req.assigned_to.username if req.assigned_to else '—'
            elif col == 'planned_date':
                row[col] = req.planned_date.strftime('%d.%m.%Y') if req.planned_date else '—'
            elif col == 'completed_date':
                row[col] = req.completed_date.strftime('%d.%m.%Y %H:%M') if req.completed_date else '—'
            elif col == 'created_at':
                row[col] = req.created_at.strftime('%d.%m.%Y')
            elif col == 'comment':
                row[col] = req.comment[:100] + '…' if len(req.comment) > 100 else req.comment
        data.append(row)
    
    if 'export' in request.GET and request.GET.get('export') == '1':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Отчёт по заявкам"
        headers = [dict(ReportForm.base_fields['columns'].choices)[col] for col in columns]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, col_name in enumerate(columns, 1):
                ws.cell(row=row_idx, column=col_idx, value=row_data.get(col_name, ''))
        for col in range(1, len(headers)+1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="report.xlsx"'
        wb.save(response)
        return response
    
    context = {
        'form': form,
        'data': data,
        'columns': columns,
        'column_labels': dict(ReportForm.base_fields['columns'].choices),
    }
    return render(request, 'requests_app/custom_report.html', context)