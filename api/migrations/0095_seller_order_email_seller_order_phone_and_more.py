# Generated by Django 4.2.3 on 2023-11-26 23:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0094_rename_melio_payout_id_payout_checkbook_payout_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='seller',
            name='order_email',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='seller',
            name='order_phone',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='sellerlocation',
            name='order_email',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sellerlocation',
            name='order_phone',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
