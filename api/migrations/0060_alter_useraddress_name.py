# Generated by Django 4.2.3 on 2023-08-18 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0059_usersellerreview_title_alter_usersellerreview_rating'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useraddress',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
