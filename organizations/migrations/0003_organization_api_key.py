# Generated by Django 3.1.1 on 2021-06-28 18:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_auto_20210401_1340"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="api_key",
            field=models.CharField(max_length=20, null=True),
        ),
    ]
