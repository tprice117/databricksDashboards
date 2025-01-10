# Generated by Django 4.2.13 on 2025-01-10 21:34

import api.managers.user
import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0087_alter_user_managers_orderpermitfee_permit'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
                ('customer_team_users', api.managers.user.CustomerTeamManager()),
            ],
        ),
    ]
