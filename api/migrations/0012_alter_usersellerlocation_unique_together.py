# Generated by Django 4.1 on 2024-06-14 16:49

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0011_orderlineitemtype_sort"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="usersellerlocation",
            unique_together={("user", "seller_location")},
        ),
    ]
