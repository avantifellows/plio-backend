# Generated by Django 3.1.1 on 2021-04-06 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_auto_20210402_1019"),
    ]

    operations = [
        migrations.CreateModel(
            name="OneTimePassword",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("mobile", models.CharField(max_length=20)),
                ("otp", models.CharField(max_length=10)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "one_time_password",
            },
        ),
    ]
