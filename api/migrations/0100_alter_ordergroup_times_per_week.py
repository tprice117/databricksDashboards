# Generated by Django 4.2.13 on 2025-02-11 17:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0099_user_stripe_id_usergroup_stripe_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordergroup',
            name='times_per_week',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Service times times per week for MainProducts that have has_service_times_per_week.', max_digits=8, null=True),
        ),
    ]
