# Generated by Django 3.1.1 on 2021-06-29 10:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_organization_api_key"),
        ("users", "0018_remove_user_auth_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="org",
                to="organizations.organization",
            ),
        ),
    ]
