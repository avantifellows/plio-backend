# Generated by Django 3.1.1 on 2021-04-01 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_auto_20210401_1325"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="role",
            name="deleted_at",
        ),
        migrations.RemoveField(
            model_name="usermeta",
            name="deleted_at",
        ),
        migrations.AddField(
            model_name="role",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="usermeta",
            name="deleted",
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]