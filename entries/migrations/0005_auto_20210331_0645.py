# Generated by Django 3.1.1 on 2021-03-31 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0004_auto_20210326_0723"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="details",
            field=models.JSONField(null=True),
        ),
    ]
