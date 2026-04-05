import os
from django.core.management.base import BaseCommand
from core.models import User


class Command(BaseCommand):
    help = "Create the initial super admin user"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="admin")
        parser.add_argument("--email", type=str, default=None)
        parser.add_argument("--password", type=str, default=None)

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"] or os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
        password = options["password"] or os.getenv("SUPER_ADMIN_PASSWORD", "admin123456")

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists. Skipping."))
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role=User.Role.SUPER_ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Super admin created: {username} / {email}\n"
            f"Password: {password}\n"
            f"Change this immediately in production!"
        ))
