# Generated by Django 4.2.11 on 2024-04-12 16:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0123_user_type'),
        ('admin_policies', '0002_alter_usergrouppolicyinvitationapproval_user_type_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='usergrouppolicypurchaseapproval',
            unique_together={('user_group', 'user_type')},
        ),
    ]
