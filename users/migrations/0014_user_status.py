# Generated by Django 3.1.1 on 2021-04-19 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_merge_20210414_0428"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[("waitlist", "Added to Waitlist"), ("approved", "Approved")],
                default="waitlist",
                max_length=255,
            ),
        ),
    ]
