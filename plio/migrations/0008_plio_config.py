# Generated by Django 3.1.1 on 2021-04-01 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0007_auto_20210401_1340"),
    ]

    operations = [
        migrations.AddField(
            model_name="plio",
            name="config",
            field=models.JSONField(null=True),
        ),
    ]
