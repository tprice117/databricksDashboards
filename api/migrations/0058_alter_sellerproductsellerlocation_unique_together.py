# Generated by Django 4.2.3 on 2023-08-14 13:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0057_remove_user_seller_user_terms_accepted_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='sellerproductsellerlocation',
            unique_together={('seller_product', 'seller_location')},
        ),
    ]
