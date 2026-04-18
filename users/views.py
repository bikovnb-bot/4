from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from .models import Profile, UserRole
from .decorators import admin_required
from .forms import UserFilterForm, ChangePasswordForm


@login_required
@admin_required
def user_list(request):
    """Список пользователей с фильтрацией и поиском"""
    users = User.objects.select_related('profile').all()
    
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
            role: User.objects.filter(profile__role=role).count()
            for role, _ in UserRole.choices
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
def user_edit(request, user_id):
    """Редактирование пользователя"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        profile = user.profile
        profile.role = role
        profile.is_active = is_active
        profile.phone = request.POST.get('phone', '')
        profile.position = request.POST.get('position', '')
        profile.save()
        
        messages.success(request, f'Пользователь {user.username} обновлён')
        return HttpResponseRedirect('/users/')
    return render(request, 'users/user_edit.html', {'user': user})


@login_required
@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} удалён')
        return HttpResponseRedirect('/users/')
    return render(request, 'users/user_confirm_delete.html', {'user': user})


@login_required
@admin_required
def user_toggle_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    profile.is_active = not profile.is_active
    profile.save()
    status = 'разблокирован' if profile.is_active else 'заблокирован'
    messages.success(request, f'Пользователь {user.username} {status}')
    return HttpResponseRedirect('/users/')


@login_required
@admin_required
def bulk_action(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')
        if not user_ids:
            messages.error(request, 'Не выбраны пользователи')
            return HttpResponseRedirect('/users/')
        if action == 'delete':
            User.objects.filter(id__in=user_ids).delete()
            messages.success(request, f'Удалено {len(user_ids)} пользователей')
        elif action == 'activate':
            Profile.objects.filter(user_id__in=user_ids).update(is_active=True)
            messages.success(request, f'Активировано {len(user_ids)} пользователей')
        elif action == 'deactivate':
            Profile.objects.filter(user_id__in=user_ids).update(is_active=False)
            messages.success(request, f'Деактивировано {len(user_ids)} пользователей')
        elif action == 'change_role':
            role = request.POST.get('new_role')
            if role:
                Profile.objects.filter(user_id__in=user_ids).update(role=role)
                messages.success(request, f'Роль изменена для {len(user_ids)} пользователей')
        return HttpResponseRedirect('/users/')


@login_required
def profile(request):
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
@admin_required
def user_change_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            user.set_password(password)
            user.save()
            messages.success(request, f'Пароль для пользователя {user.username} успешно изменён')
            return HttpResponseRedirect('/users/')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ChangePasswordForm()
    return render(request, 'users/user_change_password.html', {'form': form, 'user': user})