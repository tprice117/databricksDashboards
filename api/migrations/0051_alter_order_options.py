# Generated by Django 4.2.13 on 2024-09-10 23:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0050_alter_order_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'verbose_name': 'Transaction', 'verbose_name_plural': 'Transactions'},
        ),
    ]
