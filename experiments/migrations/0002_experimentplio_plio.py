# Generated by Django 3.1.1 on 2021-03-24 07:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("plio", "0001_initial"),
        ("experiments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="experimentplio",
            name="plio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="plio.plio"
            ),
        ),
    ]
