# Generated by Django 3.1.1 on 2021-04-12 18:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_auto_20210406_1046"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="config",
            field=models.JSONField(default=dict, null=True),
        ),
    ]