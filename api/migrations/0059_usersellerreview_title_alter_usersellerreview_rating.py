# Generated by Django 4.2.3 on 2023-08-17 19:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0058_alter_sellerproductsellerlocation_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersellerreview',
            name='title',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='usersellerreview',
            name='rating',
            field=models.IntegerField(default=5),
            preserve_default=False,
        ),
    ]
