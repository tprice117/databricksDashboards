# Generated by Django 4.1 on 2024-06-19 20:52

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("asset_management", "0002_alter_assethours_options_assetmodel_main_product"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="asset",
            name="main_product",
        ),
    ]
