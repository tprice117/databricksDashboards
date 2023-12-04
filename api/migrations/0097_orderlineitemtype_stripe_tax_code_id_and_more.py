# Generated by Django 4.2.3 on 2023-12-04 19:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0096_remove_paymentlineitem_order_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderlineitemtype',
            name='stripe_tax_code_id',
            field=models.CharField(default='txcd_20030000', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='orderlineitemtype',
            name='code',
            field=models.CharField(default='TEMP_CODE', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='orderlineitemtype',
            name='units',
            field=models.CharField(default='UNITS', max_length=255),
            preserve_default=False,
        ),
    ]
