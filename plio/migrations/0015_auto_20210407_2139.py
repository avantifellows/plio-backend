# Generated by Django 3.1.1 on 2021-04-07 21:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0014_auto_20210407_0553"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="type",
            field=models.CharField(
                choices=[("question", "Question")], default="question", max_length=255
            ),
        ),
    ]
