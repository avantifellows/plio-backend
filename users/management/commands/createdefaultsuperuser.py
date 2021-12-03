from django.core.management.base import BaseCommand
import os
from users.models import User


class Command(BaseCommand):
    help = "Creates a default superuser based on .env"

    def handle(self, *args, **options):
        superuser_email = os.environ.get("SUPERUSER_EMAIL")
        superuser_password = os.environ.get("SUPERUSER_PASSWORD")
        if not superuser_email or not superuser_password:
            print("No superuser email or password provided. Skipping.")
            return

        user = User.objects.filter(email=superuser_email).first()
        if user:
            print("User with superuser email already exists. Skipping.")
            return

        User.objects.create_superuser(
            email=superuser_email, password=superuser_password
        )
        print("Superuser created successfully!")
