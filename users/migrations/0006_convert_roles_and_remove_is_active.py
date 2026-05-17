# users/migrations/0006_convert_roles_and_remove_is_active.py

from django.db import migrations, models

def convert_roles_forward(apps, schema_editor):
    """
    Преобразование старых ролей в новые.
    Выполняется перед изменением поля choices.
    """
    Profile = apps.get_model('users', 'Profile')
    
    # Словарь отображения старых ролей в новые
    role_mapping = {
        'ADMIN': 'ADMIN',                     # остаётся
        'MANAGER': 'CONTRACT_SPECIALIST',     # менеджер -> специалист по договорам
        'VIEWER': 'WORKER',                   # наблюдатель -> рабочий
        'CONTRACTOR': 'WORKER',               # исполнитель -> рабочий
        'DISPATCHER': 'DISPATCHER',           # остаётся
    }
    
    for profile in Profile.objects.all():
        old_role = profile.role
        new_role = role_mapping.get(old_role)
        if new_role is None:
            # Если вдруг встретилась неизвестная роль, по умолчанию делаем WORKER
            new_role = 'WORKER'
        if old_role != new_role:
            profile.role = new_role
            # Сохраняем только поле role, не трогая другие
            profile.save(update_fields=['role'])

def convert_roles_backward(apps, schema_editor):
    """
    Обратное преобразование (на случай отката миграции).
    Не обязательно, но для полноты.
    """
    Profile = apps.get_model('users', 'Profile')
    reverse_mapping = {
        'CONTRACT_SPECIALIST': 'MANAGER',
        'ENGINEER': 'VIEWER',       # инженера раньше не было, откатим к VIEWER
        'WORKER': 'CONTRACTOR',     # рабочего раньше не было, откатим к CONTRACTOR
        'ADMIN': 'ADMIN',
        'DISPATCHER': 'DISPATCHER',
    }
    for profile in Profile.objects.all():
        new_role = profile.role
        old_role = reverse_mapping.get(new_role, 'VIEWER')
        if new_role != old_role:
            profile.role = old_role
            profile.save(update_fields=['role'])

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_profile_role'),
    ]

    operations = [
        # 1. Преобразуем данные ролей
        migrations.RunPython(convert_roles_forward, convert_roles_backward),
        
        # 2. Удаляем поле is_active из Profile
        migrations.RemoveField(
            model_name='profile',
            name='is_active',
        ),
        
        # 3. Изменяем поле role: увеличиваем max_length до 20 и меняем choices
        migrations.AlterField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('ADMIN', 'Администратор'), ('CONTRACT_SPECIALIST', 'Специалист по договорам'),
                         ('ENGINEER', 'Инженер'), ('DISPATCHER', 'Диспетчер'), ('WORKER', 'Рабочий')],
                db_index=True,
                default='WORKER',
                max_length=20,
                verbose_name='Роль'
            ),
        ),
    ]