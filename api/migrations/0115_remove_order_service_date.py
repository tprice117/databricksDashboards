# Generated by Django 3.2.20 on 2024-02-11 07:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0114_sellerinvoicepayable_invoice_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='service_date',
        ),
    ]
