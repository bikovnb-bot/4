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
    ProfileEditForm, GroupForm, ProfileForm
)


def get_role_display(role_code):
    return dict(UserRole.choices).get(role_code, role_code)


@login_required
@admin_required
def user_list(request):
    users = User.objects.select_related('profile').prefetch_related('groups').all()
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
        users = users.filter(is_active=True)
    elif is_active_filter == 'inactive':
        users = users.filter(is_active=False)

    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
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
        user_form = UserCreateForm(request.POST)
        profile_form = ProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            user_form.save_m2m()
            profile = user.profile
            profile.role = profile_form.cleaned_data['role']
            profile.phone = profile_form.cleaned_data['phone']
            profile.position = profile_form.cleaned_data['position']
            profile.save()
            messages.success(request, f'Пользователь {user.username} создан.')
            return redirect('users:user_list')
    else:
        user_form = UserCreateForm()
        profile_form = ProfileForm()
    return render(request, 'users/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'is_edit': False
    })


@login_required
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f'Пользователь {user.username} обновлён.')
            return redirect('users:user_list')
    else:
        user_form = UserEditForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
    return render(request, 'users/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'is_edit': True,
        'user': user
    })


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
    user.is_active = not user.is_active
    user.save()
    status = "активирован" if user.is_active else "деактивирован"
    messages.success(request, f'Пользователь {user.username} {status}.')
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

        users = User.objects.filter(id__in=user_ids).exclude(is_superuser=True).exclude(id=request.user.id)
        count = users.count()
        skipped = len(user_ids) - count
        if skipped:
            messages.warning(request, f'{skipped} пользователь(ей) пропущены (суперпользователи или вы сами).')

        if action == 'delete':
            users.delete()
            messages.success(request, f'Удалено {count} пользователей.')
        elif action == 'activate':
            users.update(is_active=True)
            messages.success(request, f'Активировано {count} пользователей.')
        elif action == 'deactivate':
            users.update(is_active=False)
            messages.success(request, f'Деактивировано {count} пользователей.')
        elif action == 'change_role':
            role = request.POST.get('new_role')
            if role and role in dict(UserRole.choices):
                Profile.objects.filter(user__in=users).update(role=role)
                messages.success(request, f'Роль изменена для {count} пользователей.')
    return redirect('users:user_list')


@login_required
def profile(request):
    """Единая страница профиля: редактирование информации и смена пароля."""
    if request.method == 'POST':
        if 'change_password' in request.POST:
            # Смена пароля
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['password'])
                request.user.save()
                messages.success(request, 'Пароль изменён. Пожалуйста, войдите заново.')
                return redirect('login')
            else:
                # Если форма пароля не валидна, отображаем страницу с ошибками
                profile_form = ProfileEditForm(instance=request.user)
                context = {
                    'form': profile_form,
                    'password_form': password_form,
                }
                return render(request, 'users/profile.html', context)
        else:
            # Редактирование профиля
            profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Ваш профиль обновлён.')
                return redirect('users:profile')
            else:
                # Если форма профиля не валидна, отображаем её с ошибками
                password_form = ChangePasswordForm()
                context = {
                    'form': profile_form,
                    'password_form': password_form,
                }
                return render(request, 'users/profile.html', context)
    else:
        profile_form = ProfileEditForm(instance=request.user)
        password_form = ChangePasswordForm()
        context = {
            'form': profile_form,
            'password_form': password_form,
        }
        return render(request, 'users/profile.html', context)


# Для обратной совместимости (если где-то используется старое имя)
profile_edit = profile
profile_password = profile


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
         'description': 'Полный доступ ко всем функциям системы: пользователи, договоры, заявки, счётчики, отчёты.'},
        {'code': 'CONTRACT_SPECIALIST', 'name': 'Специалист по договорам',
         'description': 'Управление договорами и счётчиками (создание, редактирование, просмотр). Нет доступа к заявкам.'},
        {'code': 'ENGINEER', 'name': 'Инженер',
         'description': 'Просмотр договоров, полный доступ к заявкам, управление счётчиками.'},
        {'code': 'DISPATCHER', 'name': 'Диспетчер',
         'description': 'Полный доступ к заявкам (создание, назначение, закрытие). Без доступа к договорам и счётчикам.'},
        {'code': 'WORKER', 'name': 'Рабочий',
         'description': 'Доступ только к назначенным на него заявкам (просмотр, выполнение).'},
    ]
    return render(request, 'users/role_help.html', {'roles_info': roles_info})