from django.db import migrations


def keep_api_application_secret_plaintext(apps, schema_editor):
    """
    drf-social-oauth2's convert-token flow injects the STORED client secret
    into the token request, so the API application's secret must remain
    retrievable plaintext. django-oauth-toolkit >= 2.4 hashes secrets on the
    next save unless hash_client_secret is False; existing rows (created
    plaintext under DOT 2.3) are flagged here so an incidental admin save
    cannot silently break every convert-token exchange.
    """
    Application = apps.get_model("oauth2_provider", "Application")
    Application.objects.filter(name="plio").update(hash_client_secret=False)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0021_role_deleted_by_cascade_user_deleted_by_cascade_and_more"),
        ("oauth2_provider", "0009_add_hash_client_secret"),
    ]

    operations = [
        migrations.RunPython(
            keep_api_application_secret_plaintext,
            migrations.RunPython.noop,
        ),
    ]
