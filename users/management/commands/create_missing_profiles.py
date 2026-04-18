from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile, UserRole

class Command(BaseCommand):
    help = 'Создаёт недостающие профили для пользователей'

    def handle(self, *args, **options):
        created_count = 0
        for user in User.objects.all():
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user, role=UserRole.VIEWER)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Создан профиль для {user.username}'))
        self.stdout.write(self.style.SUCCESS(f'Всего создано профилей: {created_count}'))