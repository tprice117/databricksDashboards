# Generated by Django 4.2.13 on 2024-07-18 20:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_mainproduct_has_rental_multi_step_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerProductSellerLocationRentalOneStep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('rate', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('seller_product_seller_location', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rental_one_step', to='api.sellerproductsellerlocation')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
