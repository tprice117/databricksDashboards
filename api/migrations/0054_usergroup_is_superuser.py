# Generated by Django 4.2.3 on 2023-07-28 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0053_ordergroup_tonnage_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='usergroup',
            name='is_superuser',
            field=models.BooleanField(default=False),
        ),
    ]
