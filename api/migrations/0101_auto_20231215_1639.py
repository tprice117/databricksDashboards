# Generated by Django 3.2.20 on 2023-12-15 16:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0100_usergroupcreditapplication_usergrouplegal'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usergroupcreditapplication',
            name='estimated_revenue',
        ),
        migrations.RemoveField(
            model_name='usergrouplegal',
            name='year_founded',
        ),
    ]
