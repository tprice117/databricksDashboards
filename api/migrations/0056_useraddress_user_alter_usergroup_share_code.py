# Generated by Django 4.2.3 on 2023-08-07 21:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0055_usergroup_share_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.user'),
        ),
        migrations.AlterField(
            model_name='usergroup',
            name='share_code',
            field=models.CharField(blank=True, max_length=6),
        ),
    ]
