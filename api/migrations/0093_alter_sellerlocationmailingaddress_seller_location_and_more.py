# Generated by Django 4.2.3 on 2023-11-22 20:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0092_sellerlocation_payee_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sellerlocationmailingaddress',
            name='seller_location',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mailing_address', to='api.sellerlocation'),
        ),
        migrations.AlterField(
            model_name='sellerlocationmailingaddress',
            name='street',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
