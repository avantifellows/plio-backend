import os

from django.db import migrations
from django.db.models import Q


def keep_convert_token_secret_plaintext(apps, schema_editor):
    """
    drf-social-oauth2's convert-token flow injects the STORED client secret
    into the token request, so the API application's secret must remain
    retrievable plaintext. django-oauth-toolkit >= 2.4 hashes secrets on
    save unless hash_client_secret is False.

    Two repairs, targeting the configured client id (the identifier
    drf-social-oauth2 actually looks up) with the display name as fallback:

    1. Flag the row hash_client_secret=False so future saves keep plaintext.
    2. If the stored secret is already a one-way hash (a deployment that
       migrated under a hashing DOT version), restore the canonical
       plaintext from DEFAULT_OAUTH2_CLIENT_SECRET — the environment is the
       source of truth for this credential and the hash is unrecoverable.
    """
    from django.contrib.auth.hashers import identify_hasher

    Application = apps.get_model("oauth2_provider", "Application")

    client_id = os.environ.get("DEFAULT_OAUTH2_CLIENT_ID", "")
    plaintext_secret = os.environ.get("DEFAULT_OAUTH2_CLIENT_SECRET", "")

    selector = Q(name="plio")
    if client_id:
        selector = selector | Q(client_id=client_id)

    for application in Application.objects.filter(selector):
        application.hash_client_secret = False
        update_fields = ["hash_client_secret"]
        try:
            identify_hasher(application.client_secret)
            stored_is_hashed = True
        except ValueError:
            stored_is_hashed = False
        if stored_is_hashed and plaintext_secret:
            application.client_secret = plaintext_secret
            update_fields.append("client_secret")
        # update() would skip ClientSecretField.pre_save; save() honors the
        # freshly-set hash_client_secret=False, keeping plaintext at rest
        application.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0021_role_deleted_by_cascade_user_deleted_by_cascade_and_more"),
        ("oauth2_provider", "0009_add_hash_client_secret"),
    ]

    operations = [
        migrations.RunPython(
            keep_convert_token_secret_plaintext,
            migrations.RunPython.noop,
        ),
    ]
