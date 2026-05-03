# users/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Q, Count
from .models import Profile, UserRole
from .decorators import admin_required
from .forms import (
    UserFilterForm, ChangePasswordForm, UserCreateForm, UserEditForm,
    ProfileEditForm, GroupForm
)


def get_role_display(role_code):
    return dict(UserRole.choices).get(role_code, role_code)


@login_required
@admin_required
def user_list(request):
    users = User.objects.select_related('profile').prefetch_related(
        'groups__permissions__content_type'
    ).all()
    form = UserFilterForm(request.GET)
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    is_active_filter = request.GET.get('is_active', '')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if role:
        users = users.filter(profile__role=role)
    if is_active_filter == 'active':
        users = users.filter(profile__is_active=True)
    elif is_active_filter == 'inactive':
        users = users.filter(profile__is_active=False)

    stats = {
        'total': User.objects.count(),
        'active': Profile.objects.filter(is_active=True).count(),
        'inactive': Profile.objects.filter(is_active=False).count(),
        'by_role': {
            get_role_display(rc): User.objects.filter(profile__role=rc).count()
            for rc, _ in UserRole.choices
        }
    }

    context = {
        'users': users,
        'form': form,
        'stats': stats,
        'search': search,
        'role_filter': role,
        'is_active_filter': is_active_filter,
    }
    return render(request, 'users/user_list.html', context)


@login_required
@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            form.save_m2m()
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.phone = form.cleaned_data['phone']
            profile.position = form.cleaned_data['position']
            profile.is_active = form.cleaned_data['is_active']
            profile.save()
            messages.success(request, f'Пользователь {user.username} создан.')
            return redirect('users:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'users/user_form.html', {'form': form, 'is_edit': False})


@login_required
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            # 1. Сохраняем пользователя без фиксации ManyToMany (чтобы потом вызвать save_m2m)
            user = form.save(commit=False)
            user.is_active = form.cleaned_data['is_active']   # поле теперь в Meta.fields, но страховка
            user.save()
            # 2. Сохраняем ManyToMany (группы)
            form.save_m2m()
            # 3. Обновляем поля профиля (не входят в User)
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.phone = form.cleaned_data['phone']
            profile.position = form.cleaned_data['position']
            profile.save()
            messages.success(request, f'Пользователь {user.username} обновлён.')
            return redirect('users:user_list')
    else:
        # Для GET-запроса передаём в форму начальные значения полей профиля
        initial = {
            'role': user.profile.role,
            'phone': user.profile.phone,
            'position': user.profile.position,
            'is_active': user.is_active,
        }
        form = UserEditForm(instance=user, initial=initial)
    return render(request, 'users/user_form.html', {'form': form, 'is_edit': True, 'user': user})


@login_required
@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} удалён.')
        return redirect('users:user_list')
    return render(request, 'users/user_confirm_delete.html', {'user': user})


@login_required
@admin_required
def user_toggle_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    profile.is_active = not profile.is_active
    profile.save()
    messages.success(request, f'Пользователь {user.username} {"активирован" if profile.is_active else "деактивирован"}.')
    return redirect('users:user_list')


@login_required
@admin_required
def bulk_action(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')
        if not user_ids:
            messages.error(request, 'Не выбраны пользователи.')
            return redirect('users:user_list')
        if action == 'delete':
            User.objects.filter(id__in=user_ids).delete()
            messages.success(request, f'Удалено {len(user_ids)} пользователей.')
        elif action == 'activate':
            Profile.objects.filter(user_id__in=user_ids).update(is_active=True)
            messages.success(request, f'Активировано {len(user_ids)} пользователей.')
        elif action == 'deactivate':
            Profile.objects.filter(user_id__in=user_ids).update(is_active=False)
            messages.success(request, f'Деактивировано {len(user_ids)} пользователей.')
        elif action == 'change_role':
            role = request.POST.get('new_role')
            if role:
                Profile.objects.filter(user_id__in=user_ids).update(role=role)
                messages.success(request, f'Роль изменена для {len(user_ids)} пользователей.')
    return redirect('users:user_list')


@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        if 'change_password' in request.POST:
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                user.set_password(password_form.cleaned_data['password'])
                user.save()
                messages.success(request, 'Пароль успешно изменён.')
                return redirect('users:profile')
        else:
            # Обработка профиля с файлами
            form = ProfileEditForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Профиль обновлён.')
                return redirect('users:profile')
            else:
                messages.error(request, 'Ошибка при обновлении профиля.')
    else:
        form = ProfileEditForm(instance=user)
        password_form = ChangePasswordForm()
    return render(request, 'users/profile.html', {
        'form': form,
        'password_form': password_form,
        'user': user,
    })


@login_required
@admin_required
def user_change_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Пароль для {user.username} изменён.')
            return redirect('users:user_list')
    else:
        form = ChangePasswordForm()
    return render(request, 'users/user_change_password.html', {'form': form, 'user': user})


# ---------- Группы ----------
@login_required
@admin_required
def group_list(request):
    groups = Group.objects.annotate(user_count=Count('user')).all()
    return render(request, 'users/group_list.html', {'groups': groups})


@login_required
@admin_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            group.permissions.set(form.cleaned_data['permissions'])
            messages.success(request, f'Группа "{group.name}" создана.')
            return redirect('users:group_list')
    else:
        form = GroupForm()
    return render(request, 'users/group_form.html', {'form': form, 'is_edit': False})


@login_required
@admin_required
def group_edit(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            group = form.save()
            group.permissions.set(form.cleaned_data['permissions'])
            messages.success(request, f'Группа "{group.name}" обновлена.')
            return redirect('users:group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'users/group_form.html', {'form': form, 'is_edit': True, 'group': group})


@login_required
@admin_required
def group_delete(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Группа удалена.')
        return redirect('users:group_list')
    return render(request, 'users/group_confirm_delete.html', {'group': group})


# ---------- Справочник ролей ----------
@login_required
@admin_required
def role_help(request):
    roles_info = [
        {'code': 'ADMIN', 'name': 'Администратор',
         'description': 'Полный доступ ко всем функциям системы.',
         'app_permissions': {
             'Договоры': 'Полный CRUD, импорт/экспорт.',
             'Энергоучёт': 'Управление приборами, показаниями.',
             'Заявки': 'Управление заявками, справочниками.',
             'Пользователи': 'Управление пользователями, группами, ролями.'
         }},
        {'code': 'MANAGER', 'name': 'Менеджер',
         'description': 'Управление договорами, отчётами, заявками без изменения ролей.',
         'app_permissions': {
             'Договоры': 'Создание/редактирование, добавление оплат.',
             'Энергоучёт': 'Управление приборами, импорт показаний.',
             'Заявки': 'Управление заявками, назначение исполнителей.',
             'Пользователи': 'Просмотр списка пользователей.'
         }},
        {'code': 'VIEWER', 'name': 'Наблюдатель',
         'description': 'Только просмотр.',
         'app_permissions': {
             'Договоры': 'Просмотр договоров, оплат, отчётов.',
             'Энергоучёт': 'Просмотр приборов, показаний.',
             'Заявки': 'Просмотр заявок.',
             'Пользователи': 'Нет доступа.'
         }},
        {'code': 'CONTRACTOR', 'name': 'Исполнитель',
         'description': 'Доступ только к своим договорам и заявкам.',
         'app_permissions': {
             'Договоры': 'Только свои договоры, добавление оплат.',
             'Энергоучёт': 'Просмотр своих приборов.',
             'Заявки': 'Выполнение назначенных заявок, приостановка.',
             'Пользователи': 'Нет доступа.'
         }},
        {'code': 'DISPATCHER', 'name': 'Диспетчер',
         'description': 'Управление заявками: создание, назначение, закрытие.',
         'app_permissions': {
             'Заявки': 'Создание, назначение исполнителей, закрытие заявок.',
             'Договоры': 'Просмотр договоров.',
             'Энергоучёт': 'Просмотр.',
             'Пользователи': 'Нет доступа.'
         }},
    ]
    return render(request, 'users/role_help.html', {'roles_info': roles_info})