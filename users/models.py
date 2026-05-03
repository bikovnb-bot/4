from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Администратор'
    MANAGER = 'MANAGER', 'Менеджер'
    VIEWER = 'VIEWER', 'Наблюдатель'
    CONTRACTOR = 'CONTRACTOR', 'Исполнитель'
    DISPATCHER = 'DISPATCHER', 'Диспетчер' 

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.VIEWER, verbose_name='Роль')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='Последняя активность')
    login_count = models.IntegerField(default=0, verbose_name='Количество входов')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, role=UserRole.VIEWER)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(user_logged_in)
def update_profile_on_login(sender, user, request, **kwargs):
    if hasattr(user, 'profile'):
        profile = user.profile
        profile.last_activity = timezone.now()
        profile.login_count += 1
        profile.save(update_fields=['last_activity', 'login_count'])