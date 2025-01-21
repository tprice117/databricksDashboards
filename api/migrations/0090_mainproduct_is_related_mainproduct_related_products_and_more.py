# Generated by Django 4.2.13 on 2025-01-21 19:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0089_user_push_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='mainproduct',
            name='is_related',
            field=models.BooleanField(default=False, help_text='Check this box if this product is only available as a related product.', verbose_name='Related Product Only'),
        ),
        migrations.AddField(
            model_name='mainproduct',
            name='related_products',
            field=models.ManyToManyField(blank=True, related_name='parent_products', to='api.mainproduct'),
        ),
        migrations.AddField(
            model_name='ordergroup',
            name='parent_booking',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='related_bookings', to='api.ordergroup'),
        ),
    ]
