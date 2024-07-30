# Generated by Django 4.1 on 2024-07-29 01:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0027_alter_mainproduct_default_take_rate_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mainproduct",
            name="default_take_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=20,
                help_text="Default mark up for this product (ex: 35 means 35%)",
                max_digits=18,
            ),
        ),
        migrations.AlterField(
            model_name="mainproduct",
            name="minimum_take_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=20,
                help_text="Minimum take rate for this product (ex: 10 means 10%)",
                max_digits=18,
            ),
        ),
    ]
