# Generated by Django 4.2.3 on 2023-11-10 20:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0088_alter_ordergroup_delivery_fee_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordergroup',
            name='delivery_fee',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='ordergroup',
            name='removal_fee',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=18, null=True),
        ),
    ]
