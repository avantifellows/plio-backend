# Generated by Django 3.1.1 on 2021-04-08 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_auto_20210401_1340"),
        ("users", "0010_auto_20210406_1046"),
    ]

    operations = [
        migrations.RenameField(
            model_name="organizationuser",
            old_name="role_id",
            new_name="role",
        ),
        migrations.AddField(
            model_name="user",
            name="organizations",
            field=models.ManyToManyField(
                through="users.OrganizationUser", to="organizations.Organization"
            ),
        ),
    ]
