from django.core.management.base import BaseCommand
import os
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = "Creates OAuth2 client credentials from the default oauth2 environment variables"

    def handle(self, *args, **options):
        default_oauth2_client_setup = os.environ.get(
            "DEFAULT_OAUTH2_CLIENT_SETUP", False
        )
        if not default_oauth2_client_setup:
            print("Default OAuth2 client setup is disabled. Skipping.")
            return

        default_oauth2_client_id = os.environ.get("DEFAULT_OAUTH2_CLIENT_ID")
        default_oauth2_client_secret = os.environ.get("DEFAULT_OAUTH2_CLIENT_SECRET")

        if not default_oauth2_client_id or not default_oauth2_client_secret:
            print("No default OAuth2 client id or secret provided. Skipping.")
            return

        print(
            "Default OAuth2 client id and secret provided. Creating default application."
        )
        application = Application.objects.filter(
            client_id=default_oauth2_client_id
        ).first()

        if application:
            print("An application with the default OAuth2 client id already exists. Skipping.")
            return

        Application.objects.create(
            name="default",
            client_id=default_oauth2_client_id,
            client_secret=default_oauth2_client_secret,
            redirect_uris="",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )
        print("Created default OAuth2 client id and secret!")
