# Generated by Django 3.1.1 on 2021-04-06 09:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0010_auto_20210405_0959"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="session",
            options={"ordering": ["-id"]},
        ),
    ]
