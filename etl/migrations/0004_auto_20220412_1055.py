# Generated by Django 3.1.1 on 2022-04-12 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0003_auto_20220412_1053"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bigqueryjobs",
            name="schema",
            field=models.CharField(max_length=255),
        ),
    ]
