# Generated by Django 4.2.17 on 2025-02-17 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0101_merge_20250213_2059'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordergroup',
            name='estimated_value',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
    ]
