# Generated by Django 3.1.1 on 2021-08-30 05:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0024_auto_20210830_0507"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="plio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="plio.plio"
            ),
        ),
    ]
