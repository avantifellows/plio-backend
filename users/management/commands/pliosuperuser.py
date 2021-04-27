from django.core.management.base import BaseCommand
import os
from users.models import User


class Command(BaseCommand):
    help = "Creates a default superuser based on .env"

    def handle(self, *args, **options):
        superuser_email = os.environ.get("SUPERUSER_EMAIL")
        superuser_password = os.environ.get("SUPERUSER_PASSWORD")
        if superuser_email and superuser_password:
            user = User.objects.filter(email=superuser_email).first()
            if user:
                print("User with superuser email already exists. Skipping.")
            else:
                User.objects.create_superuser(
                    email=superuser_email, password=superuser_password
                )
                print("Superuser created successfully!")
        else:
            print("No superuser email or password provided. Skipping.")
