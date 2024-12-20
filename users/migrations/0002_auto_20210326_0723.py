# Generated by Django 3.1.1 on 2021-03-26 07:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationuser",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="organizationuser",
            name="role_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING, to="users.role"
            ),
        ),
        migrations.AlterField(
            model_name="organizationuser",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="usermeta",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
