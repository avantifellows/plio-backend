# Generated by Django 3.1.1 on 2021-03-30 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0003_auto_20210326_0723"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="meta",
            field=models.JSONField(null=True),
        ),
    ]