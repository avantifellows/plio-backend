# Generated by Django 3.1.1 on 2021-06-02 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0022_auto_20210410_1537"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="is_first",
            field=models.BooleanField(default=False),
        ),
    ]
