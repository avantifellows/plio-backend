# Generated by Django 3.1.1 on 2022-02-15 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0030_merge_20220125_0510"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="survey",
            field=models.BooleanField(default=False),
        ),
    ]
