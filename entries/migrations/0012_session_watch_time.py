# Generated by Django 3.1.1 on 2021-04-06 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0011_auto_20210406_0902"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="watch_time",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
