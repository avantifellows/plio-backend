# Generated by Django 3.1.1 on 2021-04-08 05:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0013_auto_20210408_0449"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="event",
            options={"ordering": ["-id"]},
        ),
    ]
