# Generated by Django 3.1.1 on 2021-04-05 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entries", "0008_auto_20210405_0934"),
    ]

    operations = [
        migrations.AlterField(
            model_name="session",
            name="has_video_played",
            field=models.BooleanField(default=False),
        ),
    ]