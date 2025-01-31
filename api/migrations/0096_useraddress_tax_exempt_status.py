# Generated by Django 4.2.17 on 2025-01-31 18:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0095_rename_bundle_freightbundle_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='tax_exempt_status',
            field=models.CharField(blank=True, choices=[('none', 'None'), ('exempt', 'Exempt'), ('reverse', 'Reverse')], max_length=20, null=True),
        ),
    ]
