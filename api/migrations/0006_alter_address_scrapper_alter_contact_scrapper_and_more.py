# Generated by Django 4.0.4 on 2022-07-04 01:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_address_scrapper_alter_contact_scrapper_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='scrapper',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='api.scrapper'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='scrapper',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='api.scrapper'),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='scrapper',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='api.scrapper'),
        ),
    ]
