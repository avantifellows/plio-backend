# Generated by Django 3.1.1 on 2022-04-12 10:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bigqueryjobs",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="bigqueryjobs",
            name="updated_at",
        ),
    ]