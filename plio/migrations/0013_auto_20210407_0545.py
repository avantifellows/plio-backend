# Generated by Django 3.1.1 on 2021-04-07 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0012_auto_20210406_1438"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="text",
            field=models.TextField(blank=True, default=""),
        ),
    ]
