# Generated by Django 3.1.1 on 2021-06-23 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_user_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="auth_type",
            field=models.CharField(
                choices=[
                    ("default", "Default Authentication"),
                    ("avanti", "Avanti Authentication"),
                ],
                default="default",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="unique_id",
            field=models.CharField(max_length=255, null=True),
        ),
    ]
