# Generated by Django 3.2.20 on 2023-12-18 20:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0101_auto_20231215_1639'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='invoice_status',
        ),
    ]
