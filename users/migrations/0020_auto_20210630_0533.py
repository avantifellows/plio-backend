# Generated by Django 3.1.1 on 2021-06-30 05:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_organization_api_key"),
        ("users", "0019_user_org"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="org",
        ),
        migrations.AddField(
            model_name="user",
            name="auth_org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="auth_org",
                to="organizations.organization",
            ),
        ),
    ]
