# Generated by Django 4.2.13 on 2024-08-08 19:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_ordergroupservicetimesperweek_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sellerinvoicepayablelineitem',
            name='seller_invoice_payable',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.sellerinvoicepayable'),
        ),
    ]
