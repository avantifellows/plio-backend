# Generated by Django 3.1.1 on 2021-04-06 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plio', '0011_question_correct_answer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='title',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
