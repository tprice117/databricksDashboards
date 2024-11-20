# Generated by Django 4.2.13 on 2024-11-19 20:03

import common.utils.get_file_path
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0062_ordergroup_project_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, related_name='branding', to='api.usergroup')),
                ('display_name', models.CharField(default='Downstream', max_length=50)),
                ('logo', models.ImageField(blank=True, null=True, upload_to=common.utils.get_file_path.get_file_path)),
                ('primary', models.CharField(default='#018381', max_length=7)),
                ('secondary', models.CharField(default='#044162', max_length=7)),
            ],
        ),
    ]
