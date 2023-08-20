# Generated by Django 4.2.3 on 2023-08-20 22:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0063_remove_sellerproductsellerlocationmaterial_tonnage_included_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='mainproductwastetype',
            unique_together={('waste_type', 'main_product')},
        ),
        migrations.AlterUniqueTogether(
            name='productaddonchoice',
            unique_together={('product', 'add_on_choice')},
        ),
        migrations.AlterUniqueTogether(
            name='sellerproduct',
            unique_together={('product', 'seller')},
        ),
    ]
