# Generated by Django 3.1.7 on 2021-03-26 07:19

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('fladmin', '0003_auto_20210326_0712'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalulabotlist',
            name='api_token',
            field=models.TextField(default=uuid.UUID('481a2c59-3cbe-4181-a685-e5781dd33294')),
        ),
    ]
