# Generated by Django 3.1.1 on 2021-04-01 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0006_auto_20210330_1423"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="item",
            name="deleted_at",
        ),
        migrations.RemoveField(
            model_name="plio",
            name="deleted_at",
        ),
        migrations.RemoveField(
            model_name="question",
            name="deleted_at",
        ),
        migrations.RemoveField(
            model_name="video",
            name="deleted_at",
        ),
        migrations.AddField(
            model_name="item",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="plio",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="question",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="video",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]
