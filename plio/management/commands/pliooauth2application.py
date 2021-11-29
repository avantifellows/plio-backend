from django.core.management.base import BaseCommand
import os
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = "Creates OAuth2 client credentials"

    def handle(self, *args, **options):
        default_oauth2_client_setup = os.environ.get(
            "DEFAULT_OAUTH2_CLIENT_SETUP", False
        )
        default_oauth2_client_id = os.environ.get("DEFAULT_OAUTH2_CLIENT_ID")
        default_oauth2_client_secret = os.environ.get("DEFAULT_OAUTH2_CLIENT_SECRET")
        if default_oauth2_client_setup:
            if default_oauth2_client_id and default_oauth2_client_secret:
                print(
                    "Default OAuth2 client id and secret provided. Creating default application."
                )
                # user = User.objects.filter(email=superuser_email).first()
                Application.objects.create(
                    name="test",
                    client_id=default_oauth2_client_id,
                    client_secret=default_oauth2_client_secret,
                    redirect_uris="",
                    client_type=Application.CLIENT_CONFIDENTIAL,
                    authorization_grant_type=Application.GRANT_PASSWORD,
                )
                print("Created default OAuth2 client id and secret!")
            else:
                print("No default OAuth2 client id and secret provided. Skipping.")
        else:
            print("Default OAuth2 client setup is disabled. Skipping.")
