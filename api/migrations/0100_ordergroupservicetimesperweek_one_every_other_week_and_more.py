# Generated by Django 4.2.13 on 2025-02-12 12:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0099_user_stripe_id_usergroup_stripe_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordergroupservicetimesperweek',
            name='one_every_other_week',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name='sellerproductsellerlocationservicetimesperweek',
            name='one_every_other_week',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='ordergroup',
            name='times_per_week',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Service times times per week for MainProducts that have has_service_times_per_week.', max_digits=8, null=True),
        ),
    ]
