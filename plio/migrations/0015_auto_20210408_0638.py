# Generated by Django 3.1.1 on 2021-04-08 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0014_auto_20210407_0553"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="time",
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name="video",
            name="duration",
            field=models.FloatField(null=True),
        ),
    ]
