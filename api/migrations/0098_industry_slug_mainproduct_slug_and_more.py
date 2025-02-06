# Generated by Django 4.2.13 on 2025-02-06 16:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0097_sellerlocation_ein'),
    ]

    operations = [
        migrations.AddField(
            model_name='industry',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='mainproduct',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='mainproductcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='mainproductcategorygroup',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True, unique=True),
        ),
    ]
