# Generated by Django 4.2.13 on 2025-01-03 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0081_usergroup_default_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordergroup',
            name='is_delivery',
            field=models.BooleanField(default=True),
        ),
    ]
