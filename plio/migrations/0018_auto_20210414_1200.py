# Generated by Django 3.1.1 on 2021-04-14 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0017_merge_20210408_1358"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plio",
            name="is_public",
            field=models.BooleanField(default=True),
        ),
    ]