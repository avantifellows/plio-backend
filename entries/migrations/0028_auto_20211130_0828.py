# Generated by Django 3.1.1 on 2021-11-30 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0027_auto_20211124_0702"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessionanswer",
            name="answer",
            field=models.JSONField(null=True),
        ),
    ]