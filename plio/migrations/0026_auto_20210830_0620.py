# Generated by Django 3.1.1 on 2021-08-30 06:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("plio", "0025_auto_20210830_0541"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="plio.item"
            ),
        ),
    ]