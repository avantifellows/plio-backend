# Generated by Django 3.1.1 on 2021-04-01 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0002_auto_20210326_0723"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]